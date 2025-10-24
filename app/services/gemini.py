"""Lightweight Gemini 2.5 Flash Lite facade used throughout the app.

The goal of this module is not to provide real network access to Gemini but to
model the prompt flows described in the system design documentation.  Each
method synthesises deterministic-yet-rich responses so the rest of the
codebase can behave as if a real LLM was invoked.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional
from zipfile import ZipFile

KEYWORD_SECTORS = {
    "infrastructure": ["bridge", "transport", "rail", "station", "highway"],
    "energy": ["solar", "wind", "power", "grid", "battery"],
    "healthcare": ["hospital", "clinic", "medical"],
    "education": ["school", "campus", "university"],
}


@dataclass
class CandidatePersona:
    title: str
    location: Optional[str] = None
    skills: Optional[List[str]] = None
    seniority: Optional[str] = None


class GeminiService:
    """Deterministic prompt implementations inspired by the spec."""

    def __init__(self, model: str = "gemini-2.5-flash-lite", temperature: float = 0.15):
        self.model = model
        self.temperature = temperature

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
    def analyze_file(
        self,
        path: Path,
        *,
        original_name: str,
        mime_type: Optional[str] = None,
        project_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extract project insights and potential roles from a project brief."""

        text = self._extract_text(path)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        sentences = self._split_sentences(text)[:60]
        diagnostics: Dict[str, Any] = {
            "type": mime_type or path.suffix.replace(".", "") or "txt",
            "characters": len(text),
        }

        project_info = self._extract_project_info(sentences, project_context or {})
        document_type = self._classify_document(path, mime_type, lines, sentences)
        positions: List[Dict[str, Any]] = []
        job_descriptions_generated = False

        if document_type == "positions_sheet":
            positions = self._parse_positions_sheet(text, project_context or {})
            if not positions:
                positions = self._extract_positions(sentences, original_name)
        elif document_type == "job_titles":
            titles = self._extract_job_titles(lines)
            summary = project_context.get("summary") if project_context else None
            positions = [
                {
                    "title": title,
                    "department": None,
                    "experience": None,
                    "responsibilities": jd["responsibilities"],
                    "requirements": jd["requirements"],
                    "location": None,
                    "description": jd["description"],
                    "status": "draft",
                    "auto_generated": True,
                }
                for title in titles
                for jd in [self.generate_job_description({"title": title, "project_summary": summary})]
            ]
            job_descriptions_generated = bool(positions)
        else:
            positions = self._extract_positions(sentences, original_name)

        diagnostics["positions_detected"] = len(positions)
        diagnostics["project_info_detected"] = any(project_info.values())
        diagnostics["document_type"] = document_type
        diagnostics["job_descriptions_generated"] = job_descriptions_generated

        return {
            "project_info": project_info,
            "positions": positions,
            "file_diagnostics": diagnostics,
            "document_type": document_type,
            "job_descriptions_generated": job_descriptions_generated,
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
        for sentence in sentences:
            if re.search(r"(role|position|engineer|manager)", sentence, re.I):
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
                current_title = sentence.split(" - ")[0].strip().rstrip(".")
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
        nice_to_have = context.get("nice_to_have") or ["Experience with digital twin platforms", "Middle East market exposure"]
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

    def generate_outreach_email(self, payload: Dict[str, Any]) -> Dict[str, str]:
        candidate = payload.get("candidate_name", "Candidate")
        role = payload.get("title") or payload.get("role") or "Opportunity"
        highlights = payload.get("highlights") or ["mega-project exposure", "leadership runway"]
        company = payload.get("company") or "Egis"
        template = payload.get("template", "standard").lower()

        tone_by_template = {
            "standard": ("""Hi {candidate},\n\n"
                "I'm leading a search at {company} for a {role} and your profile stood out. "
                "We're assembling a taskforce that blends technical mastery with collaborative leadership. "
                "{highlights}.\n\nCould we schedule a 15 minute call this week to explore the fit?\n\n"
                "Best regards,\nEgis Talent"""),
            "executive": ("""Hello {candidate},\n\n"
                "Egis is mobilising a leadership team for a flagship programme and your track record aligns "
                "closely with what we're building. {highlights}. Let's find time to connect over the next few days.\n\n"
                "Warm regards,\nEgis Executive Talent"""),
            "technical": ("""Hi {candidate},\n\n"
                "We're standing up a delivery pod focused on advanced engineering workflows and your contributions "
                "caught our attention. {highlights}. Would you be open to a short conversation?\n\n"
                "Thanks,\nEgis Talent"""),
        }
        template_body = tone_by_template.get(template, tone_by_template["standard"])
        highlight_text = " ".join(f"• {point}" for point in payload.get("highlights", [])) or "• Impactful portfolio\n• Collaborative culture"
        body = template_body.format(candidate=candidate, company=company, role=role, highlights=highlight_text)
        subject = f"{company} | {role} opportunity"
        return {"subject": subject, "body": body}

    def generate_call_script(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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
                {"objection": "Timing", "response": "We can align interviews around your availability, including after-hours."},
                {"objection": "Relocation", "response": "We provide full mobilisation support including family assistance."},
            ],
            "closing": "I'd love to continue the conversation. I'll send a follow-up with next steps and insights.",
        }
        return {"candidate": candidate, "role": title, "location": location, "value_props": value_props, "sections": sections}

    def generate_chatbot_reply(self, history: List[Dict[str, str]], new_message: str) -> Dict[str, Any]:
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

    # ------------------------------------------------------------------
    # Research & sourcing helpers
    # ------------------------------------------------------------------
    def generate_market_research(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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

    def generate_salary_benchmark(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        base = 120000
        modifiers = [len(payload.get("title", "")) * 120, len(payload.get("region", "")) * 80]
        seniority = payload.get("seniority") or "mid"
        seniority_factor = {"junior": 0.85, "mid": 1.0, "senior": 1.2, "director": 1.45}.get(seniority.lower(), 1.0)
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

    def score_candidate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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
