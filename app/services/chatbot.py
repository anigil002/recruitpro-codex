"""Conversation orchestration helpers for the RecruitPro assistant.

The production system described in ``recruitpro_system_v2.5.md`` expects the
chatbot to do a lot more than return canned responses.  This module layers a
lightweight rule engine on top of the deterministic Gemini facade so that the
assistant can:

* keep track of the active project/position for the conversation,
* surface real project data (pipeline counts, research status, etc.),
* execute first-party tools when the user provides enough context, and
* record the evolving context back onto ``ChatbotSession.context_json``.

The goal is not to mimic a real LLM but to provide a realistic control plane so
tests and the UI can exercise end-to-end flows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy.orm import Session

from ..models import Candidate, ChatbotSession, Position, Project
from ..services.advanced_ai_features import get_feature_flag
from ..services.ai import (
    enqueue_market_research_job,
    get_or_create_salary_benchmark,
    start_sourcing_job,
)
from ..services.gemini import gemini


# ---------------------------------------------------------------------------
# Helper data structures
# ---------------------------------------------------------------------------


@dataclass
class DetectedIntent:
    """Simple intent container used by the rule engine."""

    name: Optional[str]
    confidence: float = 0.0


class ConversationContext:
    """Wrapper responsible for mutating ``session.context_json`` safely."""

    def __init__(self, raw: Optional[Dict[str, Any]] = None) -> None:
        self._data: Dict[str, Any] = dict(raw or {})

    # ------------------------------------------------------------------
    # Context accessors
    # ------------------------------------------------------------------
    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    @property
    def focused_project_id(self) -> Optional[str]:
        project = self._data.get("project_focus")
        if isinstance(project, dict):
            return project.get("project_id")
        return None

    @property
    def focused_position_id(self) -> Optional[str]:
        position = self._data.get("position_focus")
        if isinstance(position, dict):
            return position.get("position_id")
        return None

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------
    def record_user_message(self, message: str) -> None:
        history: List[str] = list(self._data.get("recent_messages", []))
        history.append(message)
        self._data["recent_messages"] = history[-10:]
        summary = " / ".join(msg.strip() for msg in history[-3:] if msg.strip())
        self._data["conversation_summary"] = summary[-300:]

    def set_last_intent(self, intent: Optional[str]) -> None:
        if intent:
            self._data["last_intent"] = intent

    def focus_project(self, project: Project) -> None:
        self._data["project_focus"] = {
            "project_id": project.project_id,
            "name": project.name,
            "sector": project.sector,
            "location": project.location_region,
            "summary": project.summary,
        }

    def focus_position(self, position: Position) -> None:
        self._data["position_focus"] = {
            "position_id": position.position_id,
            "title": position.title,
            "project_id": position.project_id,
        }

    def add_pending_job(
        self,
        *,
        job_type: str,
        job_id: str,
        project_id: Optional[str] = None,
        position_id: Optional[str] = None,
    ) -> None:
        queue: List[Dict[str, Any]] = list(self._data.get("pending_jobs", []))
        queue.append(
            {
                "job_type": job_type,
                "job_id": job_id,
                "project_id": project_id,
                "position_id": position_id,
                "requested_at": datetime.utcnow().isoformat(),
            }
        )
        self._data["pending_jobs"] = queue[-5:]

    def build_echo(self) -> Optional[str]:
        fragments: List[str] = []
        project = self._data.get("project_focus")
        if isinstance(project, dict) and project.get("name"):
            fragments.append(f"Project: {project['name']}")
        position = self._data.get("position_focus")
        if isinstance(position, dict) and position.get("title"):
            fragments.append(f"Role: {position['title']}")
        summary = self._data.get("conversation_summary")
        if isinstance(summary, str) and summary:
            fragments.append(f"Recent: {summary}")
        if not fragments:
            return None
        return " | ".join(fragments)


# ---------------------------------------------------------------------------
# Intent + entity detection
# ---------------------------------------------------------------------------


class ChatbotOrchestrator:
    """Turn chat messages into contextualised replies."""

    # Public API ---------------------------------------------------------
    def handle_message(
        self,
        db: Session,
        session: ChatbotSession,
        history: Sequence[Dict[str, str]],
        *,
        user_id: str,
        message: str,
    ) -> Dict[str, Any]:
        context = ConversationContext(session.context_json)
        context.record_user_message(message)

        project = self._resolve_project(db, user_id, message, context)
        position = self._resolve_position(db, project, message, context)
        intent = self._detect_intent(message)
        context.set_last_intent(intent.name)

        fallback_reply = gemini.generate_chatbot_reply(list(history), message)

        reply_text, tools = self._render_reply(
            db,
            fallback_reply["reply"],
            intent,
            project,
            position,
            context,
            user_id,
            message,
        )

        session.context_json = context.data
        context_echo = fallback_reply.get("context_echo") or context.build_echo()
        return {"reply": reply_text, "tools_suggested": tools, "context_echo": context_echo}

    # Internal helpers ---------------------------------------------------
    def _detect_intent(self, message: str) -> DetectedIntent:
        corpus = message.lower()

        intent_keywords: List[tuple[str, Iterable[str]]] = [
            ("status", ("status", "update", "progress", "pipeline")),
            ("market_research", ("market research", "market analysis", "research pack")),
            ("sourcing", ("sourcing", "boolean", "talent map", "source candidates")),
            ("salary", ("salary", "compensation", "benchmark", "pay range")),
            ("help", ("help", "what can you do", "capabilities")),
        ]
        intent_order = {name: index for index, (name, _keywords) in enumerate(intent_keywords)}

        scored: List[DetectedIntent] = []
        for name, keywords in intent_keywords:
            score = 0
            for keyword in keywords:
                if " " in keyword:
                    if keyword in corpus:
                        score += 1
                elif re.search(rf"\b{re.escape(keyword)}\b", corpus):
                    score += 1
            if score:
                scored.append(DetectedIntent(name=name, confidence=score))

        if not scored:
            return DetectedIntent(name=None, confidence=0.0)

        scored.sort(key=lambda item: (-item.confidence, intent_order[item.name]))
        return scored[0]

    def _resolve_project(
        self,
        db: Session,
        user_id: str,
        message: str,
        context: ConversationContext,
    ) -> Optional[Project]:
        message_lower = message.lower()
        cached = context.focused_project_id
        projects = self._load_projects(db, user_id)

        selected: Optional[Project] = None
        for project in projects:
            if project.project_id.lower() in message_lower:
                selected = project
                break
            if project.name and project.name.lower() in message_lower:
                selected = project
                break

        if not selected and cached:
            selected = db.get(Project, cached)

        if selected:
            context.focus_project(selected)
        return selected

    def _resolve_position(
        self,
        db: Session,
        project: Optional[Project],
        message: str,
        context: ConversationContext,
    ) -> Optional[Position]:
        message_lower = message.lower()
        stored_id = context.focused_position_id
        positions: List[Position] = []

        if project:
            positions = (
                db.query(Position)
                .filter(Position.project_id == project.project_id)
                .order_by(Position.created_at.desc())
                .all()
            )
        elif stored_id:
            stored = db.get(Position, stored_id)
            if stored:
                return stored

        for pos in positions:
            if pos.position_id.lower() in message_lower:
                context.focus_position(pos)
                return pos
            if pos.title and pos.title.lower() in message_lower:
                context.focus_position(pos)
                return pos

        if stored_id:
            stored = db.get(Position, stored_id)
            if stored:
                context.focus_position(stored)
                return stored
        return None

    def _render_reply(
        self,
        db: Session,
        fallback: str,
        intent: DetectedIntent,
        project: Optional[Project],
        position: Optional[Position],
        context: ConversationContext,
        user_id: str,
        message: str,
    ) -> tuple[str, List[str]]:
        tools: List[str] = []
        tool_flags = get_feature_flag(db, "chatbot.tool_suggestions") or {}

        if intent.name == "status" and project:
            reply = self._project_status_summary(db, project)
            if tool_flags.get("market_research") and not getattr(project, "research_done", 0):
                tools.append("market_research")
            return reply, tools

        if intent.name == "market_research":
            if not project:
                if tool_flags.get("market_research"):
                    tools.append("market_research")
                return (
                    "I can launch market research once you confirm the project name or ID.",
                    tools,
                )
            job = enqueue_market_research_job(db, project.project_id, user_id)
            context.add_pending_job(
                job_type="market_research",
                job_id=job.job_id,
                project_id=project.project_id,
            )
            reply = (
                f"Queued a market research refresh for {project.name}. "
                f"Job {job.job_id} is now in progress; I'll surface the findings when ready."
            )
            tools.append(f"market_research(job_id={job.job_id})")
            return reply, tools

        if intent.name == "sourcing":
            if not (project and position):
                if tool_flags.get("bulk_outreach"):
                    tools.append("bulk_outreach")
                return (
                    "Happy to start sourcing—share the position ID or title so I can launch the job.",
                    tools,
                )
            payload = {
                "project_id": project.project_id,
                "position_id": position.position_id,
                "keywords": position.requirements or [],
            }
            result = start_sourcing_job(db, payload, user_id=user_id)
            job = result["job"]
            context.add_pending_job(
                job_type="ai_sourcing",
                job_id=job.job_id,
                project_id=project.project_id,
                position_id=position.position_id,
            )
            reply = (
                f"Started AI sourcing for {position.title} ({position.position_id}). "
                f"Job {job.job_id} will build the talent map in the background."
            )
            tools.append(f"ai_sourcing(job_id={job.job_id})")
            if tool_flags.get("bulk_outreach"):
                tools.append("bulk_outreach")
            return reply, tools

        if intent.name == "salary":
            title = None
            region = None
            if position:
                title = position.title
                project = project or db.get(Project, position.project_id)
            if project:
                region = project.location_region
            if not title and project:
                first_position = (
                    db.query(Position)
                    .filter(Position.project_id == project.project_id)
                    .order_by(Position.created_at.asc())
                    .first()
                )
                if first_position:
                    title = first_position.title
            extracted = self._extract_title_and_region(message)
            title = extracted.get("title") or title
            region = extracted.get("region") or region or "GCC"

            if not title:
                if tool_flags.get("salary_benchmark"):
                    tools.append("salary_benchmark")
                return (
                    "Tell me the role title (and optionally the region) so I can run the salary benchmark.",
                    tools,
                )
            record = get_or_create_salary_benchmark(
                db,
                {"title": title, "region": region, "sector": getattr(project, "sector", None)},
                user_id=user_id,
            )
            reply = (
                f"Salary benchmark for {title} in {region}: {record.currency} {record.annual_min:,} - "
                f"{record.annual_max:,} (midpoint {record.annual_mid:,}). "
                "Sources and rationale stored on the insights tab."
            )
            tools.append("salary_benchmark")
            return reply, tools

        if intent.name == "help":
            reply = (
                "I can summarise project pipelines, launch market research, start AI sourcing, "
                "and fetch salary benchmarks. Mention the project or position and what you need."
            )
            available = [name for name, enabled in (tool_flags or {}).items() if enabled]
            if available:
                reply += f" Enabled tools: {', '.join(sorted(available))}."
            return reply, available

        # Default fallback keeps the conversation natural.
        return fallback, []

    def _project_status_summary(self, db: Session, project: Project) -> str:
        positions = (
            db.query(Position)
            .filter(Position.project_id == project.project_id)
            .order_by(Position.created_at.desc())
            .all()
        )
        candidates = db.query(Candidate).filter(Candidate.project_id == project.project_id).all()

        open_positions = sum(1 for pos in positions if (pos.status or "").lower() != "closed")
        status_fragments: List[str] = [
            f"Tracking {len(positions)} roles ({open_positions} open)."
        ]

        if candidates:
            by_status: Dict[str, int] = {}
            for cand in candidates:
                key = (cand.status or "unspecified").replace("_", " ").title()
                by_status[key] = by_status.get(key, 0) + 1
            pipeline_parts = [f"{count} {status}" for status, count in sorted(by_status.items())]
            status_fragments.append("Pipeline: " + ", ".join(pipeline_parts) + ".")
        else:
            status_fragments.append("Pipeline: no candidates yet—consider launching sourcing.")

        if project.research_status:
            status_fragments.append(f"Market research: {project.research_status}.")

        summary = f"{project.name}: " + " ".join(status_fragments)
        return summary

    def _load_projects(self, db: Session, user_id: str) -> List[Project]:
        projects = (
            db.query(Project)
            .filter(Project.created_by == user_id)
            .order_by(Project.created_at.desc())
            .limit(20)
            .all()
        )
        return projects

    def _extract_title_and_region(self, message: str) -> Dict[str, Optional[str]]:
        lower = message.lower()
        title_match = re.search(r"for ([\w\s\-/]+?)(?: role| position)", lower)
        region_match = re.search(r"in ([\w\s]+?)(?:\.|$)", lower)
        result: Dict[str, Optional[str]] = {"title": None, "region": None}
        if title_match:
            result["title"] = title_match.group(1).strip().title()
        if region_match:
            result["region"] = region_match.group(1).strip().title()
        return result


chatbot_orchestrator = ChatbotOrchestrator()

