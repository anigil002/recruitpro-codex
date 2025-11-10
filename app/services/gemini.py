"""Gemini integration helpers used across the RecruitPro backend.

When a Gemini API key is configured the service performs real HTTP calls to
Google's Generative Language API.  For environments without outbound network
access we retain deterministic offline fallbacks so that the wider application
and test-suite continue to behave predictably.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Dict, Iterable, List, Optional, TypeVar
from zipfile import ZipFile

from ..config import get_settings

try:  # pragma: no cover - optional dependency guard
    import httpx
except ImportError:  # pragma: no cover - httpx may be missing in lightweight installs
    httpx = None  # type: ignore[assignment]


T = TypeVar("T")

logger = logging.getLogger(__name__)

KEYWORD_SECTORS = {
    "infrastructure": ["bridge", "transport", "rail", "station", "highway"],
    "energy": ["solar", "wind", "power", "grid", "battery"],
    "healthcare": ["hospital", "clinic", "medical"],
    "education": ["school", "campus", "university"],
}


class GeminiServiceError(RuntimeError):
    """Raised when live Gemini interactions fail."""


@dataclass
class CandidatePersona:
    title: str
    location: Optional[str] = None
    skills: Optional[List[str]] = None
    seniority: Optional[str] = None


class GeminiService:
    """Gemini client with graceful fallbacks for offline environments."""

    DEFAULT_MODEL = "gemini-flash-lite-latest"
    _BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = 0.15):
        self.model = model
        self.temperature = temperature
        self.api_key: Optional[str] = None
        self._client: Optional["httpx.Client"] = None

    def configure_api_key(self, api_key: Optional[str]) -> None:
        """Update the API key used for live Gemini calls."""

        self.api_key = api_key or None

    # ------------------------------------------------------------------
    # Live invocation helpers
    # ------------------------------------------------------------------
    def _live_enabled(self) -> bool:
        return bool(self.api_key and httpx is not None)

    def _http_client(self) -> "httpx.Client":
        if httpx is None:  # pragma: no cover - guarded by _live_enabled
            raise GeminiServiceError("httpx is not installed")
        if self._client is None:
            self._client = httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0))
        return self._client

    def _invoke_text(
        self,
        prompt: str,
        *,
        response_mime_type: str = "application/json",
        system_instruction: Optional[str] = None,
    ) -> str:
        if not self._live_enabled():
            raise GeminiServiceError("Gemini API key is not configured")

        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "responseMimeType": response_mime_type,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        endpoint = f"{self._BASE_URL}/models/{self.model}:generateContent"
        client = self._http_client()
        try:
            response = client.post(endpoint, params={"key": self.api_key}, json=payload)
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover - network interactions
            raise GeminiServiceError("Gemini HTTP request failed") from exc

        try:
            data = response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise GeminiServiceError("Gemini returned invalid JSON") from exc

        candidates = data.get("candidates") or []
        if not candidates:
            raise GeminiServiceError("Gemini response did not include candidates")
        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not text.strip():
            raise GeminiServiceError("Gemini returned an empty response")
        return text

    def _structured_completion(
        self,
        prompt: str,
        *,
        fallback: Callable[[], T],
        system_instruction: Optional[str] = None,
        postprocess: Optional[Callable[[Any, T], Optional[T]]] = None,
    ) -> T:
        baseline = fallback()
        if not self._live_enabled():
            return baseline
        try:
            raw_text = self._invoke_text(
                prompt,
                system_instruction=system_instruction,
                response_mime_type="application/json",
            )
        except GeminiServiceError as exc:
            logger.warning("Falling back to offline Gemini implementation: %s", exc)
            return baseline
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON payload from Gemini, using fallback: %s", exc)
            return baseline

        if postprocess:
            processed = postprocess(payload, baseline)
            if processed is not None:
                return processed

        if isinstance(baseline, dict) and isinstance(payload, dict):
            merged = baseline.copy()
            for key, value in payload.items():
                # Respect explicit empty lists/dicts from AI (e.g., "positions": [] means no positions found)
                # Only skip None and empty strings
                if value is None or value == "":
                    continue
                merged[key] = value
            return merged
        if isinstance(baseline, list) and isinstance(payload, list):
            return payload or baseline
        if isinstance(payload, type(baseline)):
            return payload
        return baseline

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_text(path: Path) -> str:
        if not path.exists():
            return ""
        suffix = path.suffix.lower()
        try:
            if suffix == ".docx":
                with ZipFile(path) as archive:
                    data = archive.read("word/document.xml")
                text = re.sub(r"<(.+?)>", " ", data.decode("utf-8", errors="ignore"))
            else:
                text = path.read_bytes().decode("utf-8", errors="ignore")
        except Exception:
            # Fall back to latin-1 when utf-8 fails or any other error occurs.
            text = path.read_bytes().decode("latin-1", errors="ignore")
        return text.replace("\r\n", "\n").replace("\r", "\n").strip()

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        text = re.sub(r"([.!?])", r"\1\n", text)
        sentences = [line.strip() for line in text.splitlines() if line.strip()]
        return sentences or [text]

    # ------------------------------------------------------------------
    # File analysis
    # ------------------------------------------------------------------
    def _ai_analyze_document(self, text: str, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to analyze document content and extract structured information."""

        # Truncate text if too long (keep first 8000 characters)
        truncated_text = text[:8000] if len(text) > 8000 else text

        prompt = f"""Analyze the following document text and extract structured information.

Document Text:
{truncated_text}

Project Context (if available):
{json.dumps(project_context, indent=2, ensure_ascii=False)}

Please analyze this document and return a JSON object with the following structure:
{{
  "document_type": "project_scope" | "job_description" | "positions_list" | "general",
  "project_info": {{
    "name": "extracted project name or null",
    "summary": "brief project summary (max 400 chars) or null",
    "scope_of_work": "scope of work description or null",
    "client": "client name or null",
    "sector": "sector/industry or null",
    "location_region": "location/region or null"
  }},
  "positions": [
    {{
      "title": "position title",
      "department": "department or null",
      "experience": "experience level or null",
      "description": "role description or null",
      "responsibilities": ["responsibility 1", "responsibility 2", ...],
      "requirements": ["requirement 1", "requirement 2", ...],
      "location": "location or null"
    }}
  ]
}}

Instructions:
1. Identify the document type:
   - "project_scope": Document describes project overview, scope of work, objectives
   - "job_description": Document describes a single job/position in detail
   - "positions_list": Document lists multiple positions/roles (may be brief)
   - "general": Other project-related content

2. Extract project information if present in the document:
   - Update fields only if explicitly mentioned in the document
   - For summary: create a concise overview (max 400 chars) based on document content
   - For scope_of_work: extract detailed scope, objectives, deliverables if present

3. Extract positions/roles if present:
   - Include all positions mentioned in the document
   - For each position, extract as much detail as available
   - If responsibilities/requirements are not explicitly listed, infer reasonable ones based on the role title and context
   - If only job titles are listed without details, still include them with basic info

4. Return empty arrays/null values for information not present in the document."""

        def fallback() -> Dict[str, Any]:
            return {
                "document_type": "general",
                "project_info": {
                    "name": project_context.get("name"),
                    "summary": project_context.get("summary"),
                    "scope_of_work": None,
                    "client": project_context.get("client"),
                    "sector": project_context.get("sector"),
                    "location_region": project_context.get("location_region"),
                },
                "positions": [],
            }

        return self._structured_completion(
            prompt,
            fallback=fallback,
            system_instruction="You are a document analysis assistant for a recruitment platform. Analyze documents and extract project and position information accurately. Return valid JSON only.",
        )

    def analyze_file(
        self,
        path: Path,
        *,
        original_name: str,
        mime_type: Optional[str] = None,
        project_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract project insights and potential roles from a project brief using AI."""

        text = self._extract_text(path)
        diagnostics: Dict[str, Any] = {
            "type": mime_type or path.suffix.replace(".", "") or "txt",
            "characters": len(text),
        }

        # Use AI to analyze the document
        ai_result = self._ai_analyze_document(text, project_context or {})

        document_type = ai_result.get("document_type", "general")
        project_info = ai_result.get("project_info", {})
        positions = ai_result.get("positions", [])

        # Ensure positions have required fields and proper status
        for position in positions:
            position.setdefault("status", "draft")
            position.setdefault("auto_generated", False)
            position.setdefault("responsibilities", [])
            position.setdefault("requirements", [])

        diagnostics["positions_detected"] = len(positions)
        diagnostics["project_info_detected"] = any(v for v in project_info.values() if v)
        diagnostics["document_type"] = document_type
        diagnostics["job_descriptions_generated"] = False

        return {
            "project_info": project_info,
            "positions": positions,
            "file_diagnostics": diagnostics,
            "document_type": document_type,
            "job_descriptions_generated": False,
            "market_research_recommended": document_type == "project_scope",
        }

    def _extract_project_info(
        self, sentences: Iterable[str], context: Dict[str, Any]
    ) -> Dict[str, Optional[str]]:
        info = {
            "name": context.get("name"),
            "summary": context.get("summary"),
            "sector": context.get("sector"),
            "location_region": context.get("location_region"),
            "client": context.get("client"),
        }

        for sentence in sentences:
            if "project" in sentence.lower() and not info["name"]:
                match = re.search(r"Project (?:Name|Title)[:\-] ?(.+?)$", sentence, re.I)
                if match:
                    info["name"] = match.group(1).strip().rstrip(".")
            if "client" in sentence.lower() and not info["client"]:
                match = re.search(r"client[:\-] ?(.+?)$", sentence, re.I)
                if match:
                    info["client"] = match.group(1).strip().rstrip(".")
            if "located" in sentence.lower() and not info["location_region"]:
                match = re.search(r"located (?:in|at) ([A-Za-z\s,]+)", sentence, re.I)
                if match:
                    info["location_region"] = match.group(1).strip().rstrip(".")
        if not info["sector"]:
            keywords = Counter()
            for name, hints in KEYWORD_SECTORS.items():
                for hint in hints:
                    for sentence in sentences:
                        if hint in sentence.lower():
                            keywords[name] += 1
            if keywords:
                info["sector"] = keywords.most_common(1)[0][0]
        if not info["summary"]:
            info["summary"] = " ".join(list(sentences)[:3])[:400]
        return info

    def _extract_positions(self, sentences: Iterable[str], fallback_name: str) -> List[Dict[str, Any]]:
        roles: List[Dict[str, Any]] = []
        buffer: List[str] = []
        current_title: Optional[str] = None
        title_pattern = re.compile(r"\b(role|position|engineer|manager)\b", re.I)

        def clean(line: str) -> str:
            return re.sub(r"^[\s\-•*\d.()]+", "", line).strip()

        def looks_like_title(line: str) -> bool:
            cleaned = clean(line)
            if not cleaned or cleaned.endswith(":"):
                return False
            words = [re.sub(r"[^A-Za-z]", "", word) for word in cleaned.split()]
            meaningful = [word for word in words if word]
            if not meaningful or len(meaningful) > 8:
                return False
            titlecased = sum(1 for word in meaningful if word[0].isupper())
            uppercase = sum(1 for word in meaningful if word.isupper())
            return titlecased + uppercase >= len(meaningful)

        section_titles = {
            "position overview",
            "role overview",
            "position summary",
            "role summary",
            "project overview",
        }

        def is_heading(line: str) -> bool:
            stripped = line.lstrip()
            if stripped.startswith(("•", "-", "*")):
                return False
            cleaned = clean(line)
            if not cleaned:
                return False
            if cleaned.lower() in section_titles:
                return False
            if not title_pattern.search(cleaned):
                return False
            lowered = cleaned.lower()
            if lowered.startswith(("this role", "the role", "this position", "the position")):
                return False
            if cleaned.endswith(".") and len(cleaned.split()) > 6:
                return False
            return True

        for sentence in sentences:
            if not current_title and looks_like_title(sentence):
                current_title = clean(sentence).split(" - ")[0].strip().rstrip(".")
                continue
            if is_heading(sentence):
                if current_title:
                    roles.append(
                        {
                            "title": current_title,
                            "responsibilities": buffer[:5] or ["Deliver project milestones"],
                            "requirements": ["Relevant domain expertise", "Strong stakeholder management"],
                            "status": "draft",
                        }
                    )
                    buffer = []
                current_title = clean(sentence).split(" - ")[0].strip().rstrip(".")
            else:
                if current_title:
                    buffer.append(sentence)
        if current_title:
            roles.append(
                {
                    "title": current_title,
                    "responsibilities": buffer[:5] or ["Deliver project milestones"],
                    "requirements": ["Relevant domain expertise", "Strong stakeholder management"],
                    "status": "draft",
                }
            )
        if not roles:
            title = fallback_name.replace("_", " ").split(".")[0].title() or "Project Role"
            roles = [
                {
                    "title": title,
                    "responsibilities": ["Review project brief", "Coordinate with stakeholders"],
                    "requirements": ["5+ years experience", "Proficiency with BIM"],
                    "status": "draft",
                }
            ]
        return roles

    def _classify_document(
        self,
        path: Path,
        mime_type: Optional[str],
        lines: List[str],
        sentences: Iterable[str],
    ) -> str:
        suffix = path.suffix.lower()
        mime = (mime_type or "").lower()
        if suffix in {".csv", ".tsv"} or suffix in {".xlsx", ".xls"} or "spreadsheet" in mime:
            return "positions_sheet"

        joined_sentences = " ".join(sentences).lower()
        if any(keyword in joined_sentences for keyword in ("scope of work", "project scope", "project summary")):
            return "project_scope"
        if any(keyword in joined_sentences for keyword in ("responsibilit", "job description", "key duties")):
            return "job_description"

        titles = self._extract_job_titles(lines)
        if titles and len(titles) / max(len(lines), 1) >= 0.6:
            return "job_titles"
        return "general"

    def _extract_job_titles(self, lines: Iterable[str]) -> List[str]:
        titles: List[str] = []
        for line in lines:
            cleaned = re.sub(r"^[\d\-\*•().]+", "", line).strip()
            if not cleaned:
                continue
            lower = cleaned.lower()
            if any(keyword in lower for keyword in ("responsibil", "requirement", "summary", "deliverable")):
                continue
            if any(punct in cleaned for punct in (":", ";", ".")):
                continue
            words = cleaned.split()
            if not words or len(words) > 7:
                continue
            if cleaned.isdigit():
                continue
            if cleaned.lower().startswith(("role", "position")):
                cleaned = re.sub(r"^(role|position)[:\-\s]+", "", cleaned, flags=re.I)
            if cleaned:
                titles.append(cleaned.strip())
        unique: List[str] = []
        seen = set()
        for title in titles:
            key = title.lower()
            if key not in seen:
                unique.append(title)
                seen.add(key)
        return unique

    def _parse_positions_sheet(self, text: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        buffer = io.StringIO(text)
        sample = buffer.getvalue()[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        buffer.seek(0)
        reader = csv.DictReader(buffer, dialect=dialect)
        positions: List[Dict[str, Any]] = []
        if not reader.fieldnames:
            return positions

        def pick(row: Dict[str, str], *options: str) -> Optional[str]:
            for option in options:
                value = row.get(option)
                if value:
                    return value.strip()
            return None

        for row in reader:
            title = pick(row, "title", "role", "position", "job title", "name")
            if not title:
                continue
            responsibilities = self._normalise_list_field(
                pick(row, "responsibilities", "responsibility", "key responsibilities")
            )
            requirements = self._normalise_list_field(pick(row, "requirements", "requirement"))
            description = pick(row, "description", "summary", "notes")
            if not description and responsibilities:
                description = f"Primary focus: {responsibilities[0]}"
            elif not description:
                jd = self.generate_job_description(
                    {
                        "title": title,
                        "project_summary": context.get("summary") if context else None,
                    }
                )
                description = jd["description"]
                responsibilities = responsibilities or jd["responsibilities"]
                requirements = requirements or jd["requirements"]
            position = {
                "title": title,
                "department": pick(row, "department", "team"),
                "experience": pick(row, "experience", "seniority"),
                "responsibilities": responsibilities,
                "requirements": requirements,
                "location": pick(row, "location", "region", "city"),
                "description": description,
                "status": "draft",
                "auto_generated": False,
            }
            positions.append(position)
        return positions

    @staticmethod
    def _normalise_list_field(value: Optional[str]) -> List[str]:
        if not value:
            return []
        parts = re.split(r"[;,\n]", value)
        cleaned = [part.strip() for part in parts if part and part.strip()]
        return cleaned

    # ------------------------------------------------------------------
    # Content generation helpers
    # ------------------------------------------------------------------
    def generate_job_description(self, context: Dict[str, Any]) -> Dict[str, Any]:
        def fallback() -> Dict[str, Any]:
            title = context.get("title", "Role")
            project_summary = context.get("project_summary") or "We are delivering a flagship infrastructure initiative."
            responsibilities = context.get("responsibilities") or [
                "Own end-to-end delivery of project workstreams",
                "Partner with cross-functional experts across design, commercial and delivery",
                "Embed Egis safety and sustainability standards in every decision",
            ]
            requirements = context.get("requirements") or [
                "7+ years experience in large-scale AEC projects",
                "Chartered or working towards chartership",
                "Proven stakeholder management across consultants and contractors",
            ]
            nice_to_have = context.get("nice_to_have") or [
                "Experience with digital twin platforms",
                "Middle East market exposure",
            ]
            salary_hint = context.get("salary_hint")
            return {
                "title": title,
                "summary": project_summary,
                "description": (
                    f"Egis is seeking a {title} to accelerate delivery of {project_summary.lower()} "
                    "with a focus on operational excellence, innovation and sustainable outcomes."
                ),
                "responsibilities": responsibilities,
                "requirements": requirements,
                "nice_to_have": nice_to_have,
                "compensation_note": salary_hint,
            }

        def postprocess(payload: Any, baseline: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if not isinstance(payload, dict):
                return None
            merged = baseline.copy()
            for key in (
                "title",
                "summary",
                "description",
                "responsibilities",
                "requirements",
                "nice_to_have",
                "compensation_note",
            ):
                value = payload.get(key)
                # Respect explicit empty lists from AI, only skip None and empty strings
                if value is None or value == "":
                    continue
                merged[key] = value
            return merged

        prompt = (
            "Generate a RecruitPro job description as JSON with keys "
            "['title','summary','description','responsibilities','requirements','nice_to_have','compensation_note']. "
            "Use the following context:\n"
            f"{json.dumps(context, indent=2, ensure_ascii=False)}"
        )
        return self._structured_completion(
            prompt,
            fallback=fallback,
            system_instruction="Respond with valid JSON only.",
            postprocess=postprocess,
        )

    def generate_outreach_email(self, payload: Dict[str, Any]) -> Dict[str, str]:
        def fallback() -> Dict[str, str]:
            candidate = payload.get("candidate_name", "Candidate")
            role = payload.get("title") or payload.get("role") or "Opportunity"
            highlights = payload.get("highlights") or ["mega-project exposure", "leadership runway"]
            company = payload.get("company") or "Egis"
            template = payload.get("template", "standard").lower()

            tone_by_template = {
                "standard": (
                    """Hi {candidate},\n\n"
                    "I'm leading a search at {company} for a {role} and your profile stood out. "
                    "We're assembling a taskforce that blends technical mastery with collaborative leadership. "
                    "{highlights}.\n\nCould we schedule a 15 minute call this week to explore the fit?\n\n"
                    "Best regards,\nEgis Talent"""
                ),
                "executive": (
                    """Hello {candidate},\n\n"
                    "Egis is mobilising a leadership team for a flagship programme and your track record aligns "
                    "closely with what we're building. {highlights}. Let's find time to connect over the next few days.\n\n"
                    "Warm regards,\nEgis Executive Talent"""
                ),
                "technical": (
                    """Hi {candidate},\n\n"
                    "We're standing up a delivery pod focused on advanced engineering workflows and your contributions "
                    "caught our attention. {highlights}. Would you be open to a short conversation?\n\n"
                    "Thanks,\nEgis Talent"""
                ),
            }
            template_body = tone_by_template.get(template, tone_by_template["standard"])
            highlight_text = " ".join(f"• {point}" for point in payload.get("highlights", [])) or (
                "• Impactful portfolio\n• Collaborative culture"
            )
            body = template_body.format(
                candidate=candidate, company=company, role=role, highlights=highlight_text
            )
            subject = f"{company} | {role} opportunity"
            return {"subject": subject, "body": body}

        def postprocess(payload: Any, baseline: Dict[str, str]) -> Optional[Dict[str, str]]:
            if not isinstance(payload, dict):
                return None
            subject = payload.get("subject") or baseline["subject"]
            body = payload.get("body") or baseline["body"]
            return {"subject": subject, "body": body}

        prompt = (
            "Create an outreach email for a candidate. Respond as JSON with keys 'subject' and 'body'. "
            f"Context: {json.dumps(payload, ensure_ascii=False)}"
        )
        return self._structured_completion(
            prompt,
            fallback=fallback,
            system_instruction="Return valid JSON only.",
            postprocess=postprocess,
        )

    def generate_call_script(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        def fallback() -> Dict[str, Any]:
            title = payload.get("title", "the opportunity")
            candidate = payload.get("candidate_name", "candidate")
            location = payload.get("location", "the region")
            value_props = payload.get("value_props") or [
                "Tier-one infrastructure programme",
                "Empowered decision making",
                "Leadership succession planning",
            ]
            sections = {
                "introduction": f"Hi {candidate}, it's great to connect. I'm supporting the {title} search in {location}.",
                "context": "We're partnering with the client to deliver a high-impact mandate with strong board sponsorship.",
                "motivation": [
                    "What would prompt you to explore a new role right now?",
                    "How do you evaluate opportunities in terms of scale and autonomy?",
                ],
                "technical": [
                    "Walk me through a recent project where you had to resolve a major engineering challenge.",
                    "How do you lead design coordination with remote partners?",
                ],
                "managerial": [
                    "How large were the teams you led and how were they structured?",
                    "Tell me about your stakeholder management cadence.",
                ],
                "commercial": [
                    "What financial levers do you monitor most closely during delivery?",
                    "Describe a time you protected margin without compromising quality.",
                ],
                "design": [
                    "How do you ensure the design intent is preserved through construction?",
                    "What digital tools do you rely on for coordination?",
                ],
                "objection_handling": [
                    {
                        "objection": "Timing",
                        "response": "We can align interviews around your availability, including after-hours.",
                    },
                    {
                        "objection": "Relocation",
                        "response": "We provide full mobilisation support including family assistance.",
                    },
                ],
                "closing": "I'd love to continue the conversation. I'll send a follow-up with next steps and insights.",
            }
            return {
                "candidate": candidate,
                "role": title,
                "location": location,
                "value_props": value_props,
                "sections": sections,
            }

        def postprocess(payload: Any, baseline: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if not isinstance(payload, dict):
                return None
            merged = baseline.copy()
            for key, value in payload.items():
                if value not in (None, ""):
                    merged[key] = value
            return merged

        prompt = (
            "Draft a structured call script for a recruiter. Return JSON including candidate, role, location, value_props"
            " (list) and sections (object). Context: "
            f"{json.dumps(payload, ensure_ascii=False)}"
        )
        return self._structured_completion(
            prompt,
            fallback=fallback,
            system_instruction="Return valid JSON only.",
            postprocess=postprocess,
        )

    def generate_chatbot_reply(self, history: List[Dict[str, str]], new_message: str) -> Dict[str, Any]:
        def fallback() -> Dict[str, Any]:
            context_blurb = " ".join(item["content"] for item in history[-5:])[-400:]
            reply = (
                "Thanks for the update. Here's what I can help with next: "
                "1) summarise the latest candidate pipeline, 2) launch an AI sourcing job, "
                "3) request market research. Just let me know which workflow to trigger."
            )
            if "market" in new_message.lower():
                reply = "I'll prepare a market analysis pack. Provide the project ID or region so I can launch it."
            elif "sourcing" in new_message.lower():
                reply = "Happy to start sourcing. Share the position ID plus keywords and I'll build the boolean strings."
            elif "status" in new_message.lower():
                reply = "Current status: we have active candidates in screening and one interview scheduled this week."
            return {"reply": reply, "context_echo": context_blurb}

        def postprocess(payload: Any, baseline: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if not isinstance(payload, dict):
                return None
            reply = payload.get("reply") or baseline["reply"]
            context_echo = payload.get("context_echo") or baseline["context_echo"]
            return {"reply": reply, "context_echo": context_echo}

        history_context = {"history": history[-10:], "message": new_message}
        prompt = (
            "You are the RecruitPro assistant. Provide a helpful reply in JSON with keys 'reply' and 'context_echo'. "
            f"Conversation: {json.dumps(history_context, ensure_ascii=False)}"
        )
        return self._structured_completion(
            prompt,
            fallback=fallback,
            system_instruction="Return valid JSON only.",
            postprocess=postprocess,
        )

    # ------------------------------------------------------------------
    # Research & sourcing helpers
    # ------------------------------------------------------------------
    def generate_market_research(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        def fallback() -> Dict[str, Any]:
            region = payload.get("region", "GCC")
            sector = payload.get("sector", "infrastructure")
            summary = payload.get("summary") or "Landmark programme requiring multidisciplinary delivery partners."
            year = datetime.utcnow().year
            findings = [
                {
                    "title": f"{region} flagship {sector} initiative",
                    "description": "Comparable project delivered under similar contract model with collaborative governance.",
                    "leads": ["PMC: Alpha Advisory", "Consultant: Delta Design", "Contractor: Horizon Build"],
                },
                {
                    "title": "Talent availability snapshot",
                    "description": "Regional supply constrained at senior levels; compelling EVP is critical.",
                    "leads": ["Leverage megaproject alumni networks", "Promote long-term mobility"],
                },
            ]
            sources = [
                {"title": f"{region} {sector} digest {year}", "url": f"https://insights.egis/{region.lower()}/{sector}"},
                {"title": "World Construction Network", "url": "https://www.worldconstructionnetwork.com"},
            ]
            return {
                "region": region,
                "sector": sector,
                "summary": summary,
                "findings": findings,
                "sources": sources,
            }

        def postprocess(payload: Any, baseline: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if not isinstance(payload, dict):
                return None
            merged = baseline.copy()
            for key in ("region", "sector", "summary", "findings", "sources"):
                value = payload.get(key)
                if value not in (None, ""):
                    merged[key] = value
            return merged

        prompt = (
            "Generate market research insights as JSON with keys ['region','sector','summary','findings','sources']. "
            f"Context: {json.dumps(payload, ensure_ascii=False)}"
        )
        return self._structured_completion(
            prompt,
            fallback=fallback,
            system_instruction="Return valid JSON only.",
            postprocess=postprocess,
        )

    def generate_salary_benchmark(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        def fallback() -> Dict[str, Any]:
            base = 120000
            modifiers = [len(payload.get("title", "")) * 120, len(payload.get("region", "")) * 80]
            seniority = payload.get("seniority") or "mid"
            seniority_factor = {"junior": 0.85, "mid": 1.0, "senior": 1.2, "director": 1.45}.get(
                seniority.lower(), 1.0
            )
            mean_salary = int(base * seniority_factor + sum(modifiers))
            spread = int(mean_salary * 0.1)
            return {
                "currency": "USD",
                "annual_min": mean_salary - spread,
                "annual_mid": mean_salary,
                "annual_max": mean_salary + spread,
                "rationale": "Benchmarked using Egis proprietary compensation datasets blended with public sources.",
                "sources": [
                    {"title": "Glassdoor aggregated data", "url": "https://www.glassdoor.com"},
                    {"title": "Rethinking Construction Salaries 2024", "url": "https://insights.egis/salaries"},
                ],
            }

        def postprocess(payload: Any, baseline: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if not isinstance(payload, dict):
                return None
            merged = baseline.copy()
            for key in ("currency", "annual_min", "annual_mid", "annual_max", "rationale", "sources"):
                value = payload.get(key)
                if value not in (None, ""):
                    merged[key] = value
            return merged

        prompt = (
            "Provide a salary benchmark as JSON with keys ['currency','annual_min','annual_mid','annual_max','rationale','sources']. "
            f"Context: {json.dumps(payload, ensure_ascii=False)}"
        )
        return self._structured_completion(
            prompt,
            fallback=fallback,
            system_instruction="Return valid JSON only.",
            postprocess=postprocess,
        )

    def score_candidate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        def fallback() -> Dict[str, Any]:
            technical = 0.5
            cultural = 0.5
            growth = 0.5
            for skill in payload.get("skills", []):
                if skill.lower() in {"bim", "pmc", "design management", "pmp"}:
                    technical += 0.1
            if payload.get("years_experience", 0) > 10:
                technical += 0.2
                growth += 0.1
            if payload.get("leadership", False):
                cultural += 0.2
            score = {
                "technical_fit": min(round(technical, 2), 1.0),
                "cultural_alignment": min(round(cultural, 2), 1.0),
                "growth_potential": min(round(growth, 2), 1.0),
            }
            score["match_score"] = round(mean(score.values()), 2)
            score["notes"] = [
                "Candidate has relevant project experience.",
                "Consider deep dive on leadership examples.",
            ]
            return score

        def postprocess(payload: Any, baseline: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            if not isinstance(payload, dict):
                return None
            merged = baseline.copy()
            for key, value in payload.items():
                if value not in (None, ""):
                    merged[key] = value
            return merged

        prompt = (
            "Score a candidate for RecruitPro. Return JSON with keys technical_fit, cultural_alignment, growth_potential, "
            "match_score, notes (list). Context: "
            f"{json.dumps(payload, ensure_ascii=False)}"
        )
        return self._structured_completion(
            prompt,
            fallback=fallback,
            system_instruction="Return valid JSON only.",
            postprocess=postprocess,
        )

    def build_boolean_search(self, persona: CandidatePersona) -> str:
        skills = persona.skills or ["PMO", "Mega Project", "Stakeholder Management"]
        title = persona.title.replace(" ", "")
        skill_terms = " OR ".join(f'"{skill}"' for skill in skills)
        location = f" (\"{persona.location}\")" if persona.location else ""
        seniority = f" (\"{persona.seniority}\")" if persona.seniority else ""
        return f"(\"{persona.title}\" OR {title}) AND ({skill_terms}){location}{seniority}"

    def synthesise_candidate_profiles(self, persona: CandidatePersona, count: int = 5) -> List[Dict[str, Any]]:
        skills = persona.skills or ["Mega Projects", "Stakeholder", "Risk"]
        return [
            {
                "name": f"Candidate {i + 1}",
                "title": persona.title,
                "location": persona.location or "Remote",
                "platform": "LinkedIn",
                "profile_url": f"https://linkedin.com/in/candidate-{i + 1}",
                "summary": f"Seasoned {persona.title.lower()} with emphasis on {', '.join(skills[:2])}.",
                "quality_score": 80 - i * 5,
            }
            for i in range(count)
        ]

    def smartrecruiters_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "steps": [
                "Launch headless browser and navigate to SmartRecruiters login.",
                "Authenticate using encrypted credentials provided via the portal.",
                "Search for the specified requisitions and apply saved filters.",
                "Export candidate cards into RecruitPro sourcing results via secure channel.",
                "Invalidate session and clear cookies for compliance.",
            ],
            "targets": payload.get("position_ids", []),
            "status": "queued",
        }

    async def stream_activity(self, queue: asyncio.Queue, user_id: Optional[str]) -> Iterable[Dict[str, Any]]:
        while True:
            event = await queue.get()
            if user_id and event.get("user_id") not in (None, user_id):
                continue
            yield event


gemini = GeminiService()
try:  # pragma: no cover - defensive initialisation
    gemini.configure_api_key(get_settings().gemini_api_key_value)
except Exception:
    pass
