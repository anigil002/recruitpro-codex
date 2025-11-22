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

try:
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
        before_sleep_log,
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

try:  # pragma: no cover - optional dependency guard
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - fitz may be missing in lightweight installs
    fitz = None  # type: ignore[assignment]

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

    DEFAULT_MODEL = "gemini-2.5-flash-lite"
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

    def _invoke_text_core(
        self,
        prompt: str,
        *,
        response_mime_type: str = "application/json",
        system_instruction: Optional[str] = None,
    ) -> str:
        """Core Gemini API invocation without retry logic."""
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
            logger.warning(f"Gemini HTTP request failed: {exc}")
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

    def _invoke_text(
        self,
        prompt: str,
        *,
        response_mime_type: str = "application/json",
        system_instruction: Optional[str] = None,
    ) -> str:
        """Invoke Gemini API with automatic retry logic for transient failures."""
        if TENACITY_AVAILABLE:
            # Use retry logic when tenacity is available
            @retry(
                retry=retry_if_exception_type(GeminiServiceError),
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=2, max=10),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True,
            )
            def _invoke_with_retry():
                return self._invoke_text_core(
                    prompt,
                    response_mime_type=response_mime_type,
                    system_instruction=system_instruction,
                )

            return _invoke_with_retry()
        else:
            # Fall back to direct invocation without retry
            return self._invoke_text_core(
                prompt,
                response_mime_type=response_mime_type,
                system_instruction=system_instruction,
            )

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
                if value not in (None, "", [], {}):
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
            if suffix == ".pdf":
                # Handle PDF files with PyMuPDF (fitz)
                if fitz is None:
                    logger.warning("PyMuPDF not installed, falling back to raw bytes")
                    text = path.read_bytes().decode("utf-8", errors="ignore")
                else:
                    try:
                        doc = fitz.open(str(path))
                        text_parts = []
                        for page in doc:
                            page_text = page.get_text()
                            if page_text:
                                text_parts.append(page_text)
                        doc.close()
                        text = "\n".join(text_parts)
                    except Exception as exc:
                        logger.warning(f"Failed to extract text from PDF with PyMuPDF: {exc}, falling back to raw bytes")
                        text = path.read_bytes().decode("utf-8", errors="ignore")
            elif suffix == ".docx":
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

        # Truncate text if too long (keep first 50000 characters for better parsing of multi-position documents)
        truncated_text = text[:50000] if len(text) > 50000 else text

        prompt = f"""Task
Analyze the provided document and return structured project and job information.
The document may be:
    • a project scope/summary
    • a single job description
    • a list of multiple job descriptions
    • a mix of project scope and one or more job descriptions

You must:
    1. Correctly classify the document type.
    2. Extract project_info if project details exist.
    3. Extract all positions if any job descriptions exist.

⸻

Input

Document Text:
{truncated_text}

Optional Project Context (JSON):
{json.dumps(project_context, indent=2, ensure_ascii=False)}

⸻

Output Schema (RecruitPro Standard)

Return a single valid JSON object with this exact structure:

{{
  "document_type": "project_scope" | "job_description" | "positions_list" | "mixed" | "general",
  "project_info": {{
    "name": "string|null",
    "summary": "string|null",
    "scope_of_work": "string|null",
    "client": "string|null",
    "sector": "string|null",
    "location_region": "string|null"
  }},
  "positions": [
    {{
      "title": "string",
      "department": "string|null",
      "experience": "string|null",
      "qualifications": ["string", "..."],
      "description": "string|null",
      "responsibilities": ["string", "..."],
      "requirements": ["string", "..."],
      "location": "string|null"
    }}
  ]
}}

    • positions must contain one object per distinct role.
    • All keys must always be present. Use null or [] when data is missing.

⸻

Document Type Logic (document_type)

Set document_type using these rules:
    • "project_scope"
The document mainly describes a project, its context, objectives, or scope of work, with no meaningful job descriptions.
    • "job_description"
The document primarily describes one role in detail (even if it mentions a project).
    • "positions_list"
The document's main purpose is to list multiple roles (e.g., hiring matrix, "we're hiring" list, staffing table), with little or no project detail.
    • "mixed"
The document contains both:
    • meaningful project information (overview, scope, client, etc.), and
    • one or more job descriptions/roles.
    • "general"
Other project-related or HR-related content that does not fit the above categories.

Even if document_type is project_scope, job_description, positions_list, or mixed, you must still try to populate both project_info and positions whenever relevant information appears.

⸻

Extraction Rules

1. Strict Extraction (No Inference)
    • Extract only information explicitly present in the document text (and table cells).
    • Do not guess or invent responsibilities, requirements, qualifications, or project details.
    • If a value is missing in the source:
    • Use null for string/object fields.
    • Use [] for arrays.
    • Never omit any keys defined in the schema.

2. Project Info (project_info)
    • Extract from the Document Text first.
    • Then use Optional Project Context (JSON) only to fill fields that are still null.
    • If both document and context provide a value, the document text wins.
    • summary must be a concise overview (≤400 characters) if the document provides enough information.
    • Populate scope_of_work with explicit scope, objectives, or deliverables if present.

3. Positions (positions)
    • Scan the entire document (paragraphs, bullet points, tables, headings).
    • Extract every distinct role:
    • A document can have 1, 5, 10, or 20+ roles — include them all.
    • Each role must be a separate object in the positions array.
    • For each position, fill:
    • title
    • department
    • experience
    • qualifications[]
    • description
    • responsibilities[]
    • requirements[]
    • location
    • If a field is not present for a specific role, use null or [].

4. Tables & Structured Lists
When the document contains tables or aligned columns:
    • Treat each data row as a potential position.
    • Map header/column names to schema fields:
    • Role / Position / Title → title
    • Department / Division → department
    • Experience → experience
    • Qualifications / Education → qualifications[]
    • Responsibilities / Duties → responsibilities[]
    • Requirements / Skills → requirements[]
    • Location / Region → location
    • Combine all cells from the same row into a single position object.
    • Skip header rows and non-data rows.
    • If a cell contains multiple bullet points or lines, split them into separate items in the corresponding array.

5. Valid Job Title Filtering
A valid title must:
    • Be a specific role or designation (typically 2–8 words).
    • Clearly indicate a job/position (e.g., "Senior Electrical Engineer", "Project Manager – Airfield", "HSE Lead").

Do not treat these as titles:
    • Sentences starting with:
"Minimum of…", "Experience in…", "Ability to…", "Registered Professional…"
    • Long qualification sentences (>10 words).
    • Generic phrases like "engineering position at major airports".
    • Phrases ending with "position", "role", or "experience" without a concrete title.

⸻

Output Constraints
    • The final answer must be only one JSON object, matching the schema.
    • Do not include any explanations, markdown, comments, or extra text.
    • Ensure JSON syntax is valid: proper quotes, commas, and arrays."""

        def fallback() -> Dict[str, Any]:
            # Even without AI, try to extract positions using heuristic methods
            sentences = self._split_sentences(truncated_text)
            heuristic_positions = self._extract_positions(sentences, "uploaded_document")

            # Extract project info using heuristics
            project_info = self._extract_project_info(sentences, project_context)

            return {
                "document_type": "general",
                "project_info": project_info,
                "positions": heuristic_positions,
            }

        return self._structured_completion(
            prompt,
            fallback=fallback,
            system_instruction="You are a document analysis assistant for RecruitPro. Extract only information explicitly present in documents. Do not infer or invent data. Return valid JSON only matching the RecruitPro Standard schema.",
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
            position.setdefault("qualifications", [])
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
        title_pattern = re.compile(r"\b(lead|director|manager|engineer|coordinator|specialist|analyst)\b", re.I)

        def clean(line: str) -> str:
            return re.sub(r"^[\s\-•*\d.()]+", "", line).strip()

        def is_invalid_title(text: str) -> bool:
            """Check if the text is NOT a valid job title (e.g., it's a qualification or requirement)."""
            text_lower = text.lower()
            # Reject if it starts with qualification indicators
            if any(text_lower.startswith(prefix) for prefix in [
                "minimum of", "minimum", "registered professional", "experience in", "experience with",
                "ability to", "demonstrated", "demonstrable", "strong", "excellent", "thorough",
                "knowledge of", "familiarity", "proficiency"
            ]):
                return True
            # Reject if it's too long (more than 10 words typically means it's not a title)
            if len(text.split()) > 10:
                return True
            # Reject vague position descriptions
            if any(phrase in text_lower for phrase in [
                "position at", "role in", "experience in", "licensed to practice"
            ]):
                return True
            return False

        def looks_like_title(line: str) -> bool:
            cleaned = clean(line)
            if not cleaned or cleaned.endswith(":"):
                return False
            # Reject invalid titles
            if is_invalid_title(cleaned):
                return False
            words = [re.sub(r"[^A-Za-z/]", "", word) for word in cleaned.split()]
            meaningful = [word for word in words if word and len(word) > 1]
            if not meaningful or len(meaningful) > 8:
                return False
            # Check if it has title-case formatting
            titlecased = sum(1 for word in meaningful if word[0].isupper())
            uppercase = sum(1 for word in meaningful if word.isupper())
            # Must have title pattern keywords or be mostly title-cased
            has_title_keywords = title_pattern.search(cleaned)
            is_mostly_titlecased = (titlecased + uppercase) >= len(meaningful) * 0.7
            return has_title_keywords or is_mostly_titlecased

        section_titles = {
            "position overview",
            "role overview",
            "position summary",
            "role summary",
            "project overview",
            "qualifications and experience",
            "qualifications",
            "responsibilities",
            "requirements",
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
            # Reject invalid titles
            if is_invalid_title(cleaned):
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
                if value not in (None, "", []):
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
            """Generate realistic salary estimates based on industry benchmarks and role characteristics."""

            # Base salary ranges by role type (USD, annual)
            role_bases = {
                "engineer": 85000,
                "manager": 105000,
                "director": 145000,
                "specialist": 75000,
                "coordinator": 65000,
                "analyst": 70000,
                "architect": 90000,
                "consultant": 95000,
                "lead": 110000,
                "executive": 175000,
            }

            # Seniority multipliers
            seniority_factors = {
                "junior": 0.70,
                "mid": 1.0,
                "senior": 1.30,
                "principal": 1.50,
                "director": 1.65,
                "vp": 1.85,
                "c-level": 2.20,
            }

            # Regional cost-of-living adjustments
            region_factors = {
                "gcc": 1.25,  # GCC (tax-free, expat packages)
                "middle east": 1.20,
                "uae": 1.30,
                "saudi": 1.25,
                "qatar": 1.28,
                "us": 1.15,
                "uk": 1.05,
                "europe": 1.00,
                "asia": 0.85,
                "australia": 1.10,
            }

            # Sector complexity adjustments
            sector_factors = {
                "infrastructure": 1.15,
                "aviation": 1.20,
                "rail": 1.15,
                "energy": 1.25,
                "healthcare": 1.10,
                "buildings": 1.00,
            }

            # Extract parameters
            title = (payload.get("title") or "").lower()
            region = (payload.get("region") or "").lower()
            sector = (payload.get("sector") or "").lower()
            seniority = (payload.get("seniority") or "mid").lower()

            # Determine base salary from title
            base = 80000  # Default fallback
            for role_type, role_base in role_bases.items():
                if role_type in title:
                    base = role_base
                    break

            # Apply multipliers
            seniority_mult = seniority_factors.get(seniority, 1.0)

            region_mult = 1.0
            for reg, factor in region_factors.items():
                if reg in region:
                    region_mult = factor
                    break

            sector_mult = 1.0
            for sect, factor in sector_factors.items():
                if sect in sector:
                    sector_mult = factor
                    break

            # Calculate final salary
            mean_salary = int(base * seniority_mult * region_mult * sector_mult)
            spread_pct = 0.15  # 15% spread for range
            spread = int(mean_salary * spread_pct)

            return {
                "currency": "USD",
                "annual_min": mean_salary - spread,
                "annual_mid": mean_salary,
                "annual_max": mean_salary + spread,
                "rationale": f"Market benchmark for {seniority} {title} in {region or 'global market'}. Based on industry compensation data for {sector or 'construction/engineering'} sector. Note: AI API unavailable, using offline benchmark database.",
                "sources": [
                    {"title": "Glassdoor Salary Data", "url": "https://www.glassdoor.com"},
                    {"title": "PayScale Industry Reports", "url": "https://www.payscale.com"},
                    {"title": "Robert Half Salary Guide", "url": "https://www.roberthalf.com/salary-guide"},
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

    def screen_cv(
        self,
        path: Path,
        *,
        original_name: str,
        position_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Screen a candidate CV using detailed Egis Middle East & North America screening criteria."""

        text = self._extract_text(path)

        # IMPORTANT: Analyze the ENTIRE CV - no truncation for comprehensive analysis
        # The new prompt requires full CV analysis
        cv_text = text

        # Build position context string
        position_info = ""
        if position_context:
            position_info = f"""
Job Description / Position Context:
{json.dumps(position_context, indent=2, ensure_ascii=False)}
"""

        system_instruction = {
            "role": "Senior Talent Acquisition Partner for Egis Middle East & North America",
            "specialization": "Screening CVs for construction, engineering, project management, aviation, rail, buildings, and infrastructure roles within large capital programs",
            "tone": "Professional, efficient, analytical, and evidence-based",
            "compliance_rules": [
                "Read and analyze the entire CV — all pages, all sections, all appendices",
                "No truncation - use 100% of available CV content",
                "All statements must be grounded in the CV or provided context",
                "No fabricated or speculative data",
                "Use objective, factual, and professional tone"
            ]
        }

        prompt = f"""You are a Senior Talent Acquisition Partner for Egis Middle East & North America.
You specialize in screening CVs for construction, engineering, project management, aviation, rail, buildings, and infrastructure roles within large capital programs.
Your tone is professional, efficient, analytical, and evidence-based.

GLOBAL PROCESSING RULES

1. Full CV Analysis (No Truncation)
   - You must read and analyse the entire CV — all pages, all sections, all appendices.
   - Do not limit analysis to the first few hundred words, top section, opening summary, or first page.
   - Use 100% of the available CV content for your assessment.

2. Role Matching
   - If a specific role or JD is provided → strictly use that role for screening.
   - If no role is provided → determine the most suitable Egis role(s) from construction, engineering, project management, aviation, rail, buildings, and infrastructure positions.

3. Must-Have Requirement Extraction
   - From the job description, identify:
     * Minimum experience
     * Sector exposure
     * Technical competencies
     * Certifications
     * Software
     * Education
     * Canadian experience (if applicable)
     * Stakeholder/client-facing requirements
     * Communication / leadership expectations
     * Location or mobility requirements
   - Every must-have requirement must appear in the compliance table.
   - No skipping. No merging.

4. Compliance Classification
   - For each requirement in the JD, classify the candidate using:
     * ✅ Complying — requirement fully met and explicitly supported by CV evidence
     * ❌ Not Complying — requirement not met or explicitly contradicted
     * ⚠️ Not Mentioned / Cannot Confirm — CV does not provide evidence
   - Compliance must always be supported by specific, quoted or paraphrased evidence from the CV.

{position_info}

CV Content:
{cv_text}

You must return a JSON object with the following structure:

{{
  "candidate": {{
    "name": "string (REQUIRED - extract from CV)",
    "email": "string or null",
    "phone": "string or null"
  }},

  "table_1_screening_summary": {{
    "overall_fit": "Strong Match | Potential Match | Low Match",
    "recommended_roles": ["string - e.g., Senior Project Manager, Track Engineer, Pavement Specialist"],
    "key_strengths": [
      "string - Bullet point 1",
      "string - Bullet point 2",
      "string - Bullet point 3",
      "string - Bullet point 4"
    ],
    "potential_gaps": [
      "string - Bullet point 1",
      "string - Bullet point 2"
    ],
    "notice_period": "string - As stated on CV or 'Not Mentioned'"
  }},

  "table_2_compliance": [
    {{
      "requirement_category": "string - e.g., Education, Total Experience, Sector/Domain, Canadian Experience, Technical Skills, Software, Certifications, Stakeholder Engagement, Communication Skills, Mobility/Relocation",
      "requirement_description": "string - Detailed description of the requirement from JD",
      "compliance_status": "✅ Complying | ❌ Not Complying | ⚠️ Not Mentioned / Cannot Confirm",
      "evidence": "string - Specific evidence from CV supporting the compliance status"
    }}
  ],

  "final_recommendation": {{
    "summary": "string - A concise 3-4 sentence summary covering: strength of match, key risk factors, compliance gaps",
    "decision": "Proceed to technical interview | Suitable for a lower-grade role | Reject",
    "justification": "string - Clear justification for the decision"
  }},

  "record_management": {{
    "screened_at_utc": "ISO-8601 datetime string",
    "screened_by": "Senior Talent Acquisition Partner",
    "tags": ["string"]
  }}
}}

IMPORTANT:
- You MUST extract the candidate's name from the CV
- Extract email and phone if available
- Analyze the ENTIRE CV - do not truncate or skip sections
- Extract only evidence-based insights directly from the CV
- Be factual and objective - do not invent or speculate data
- All compliance assessments must be supported by specific CV evidence
- Use the current timestamp for screened_at_utc
- Return only valid JSON"""

        def fallback() -> Dict[str, Any]:
            # Extract basic information using heuristic methods
            lines = cv_text.split('\n')
            candidate_name = "Unknown Candidate"
            email = None
            phone = None

            # Try to extract name from first few lines
            for line in lines[:10]:
                line = line.strip()
                if line and len(line.split()) <= 4 and not any(char in line for char in ['@', 'http', ':', '•']):
                    if not any(keyword in line.lower() for keyword in ['curriculum', 'vitae', 'resume', 'cv', 'profile']):
                        candidate_name = line
                        break

            # Try to extract email
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            email_match = re.search(email_pattern, cv_text)
            if email_match:
                email = email_match.group(0)

            # Try to extract phone
            phone_pattern = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}'
            phone_match = re.search(phone_pattern, cv_text)
            if phone_match:
                phone = phone_match.group(0)

            return {
                "candidate": {
                    "name": candidate_name,
                    "email": email,
                    "phone": phone
                },
                "table_1_screening_summary": {
                    "overall_fit": "Potential Match",
                    "recommended_roles": ["CV analysis pending"],
                    "key_strengths": ["CV analysis pending - AI screening unavailable"],
                    "potential_gaps": ["Full screening analysis pending"],
                    "notice_period": "Not Mentioned"
                },
                "table_2_compliance": [
                    {
                        "requirement_category": "General",
                        "requirement_description": "Full CV screening",
                        "compliance_status": "⚠️ Not Mentioned / Cannot Confirm",
                        "evidence": "Basic extraction completed, full AI screening unavailable"
                    }
                ],
                "final_recommendation": {
                    "summary": "Basic candidate information extracted. Full AI screening was unavailable. Manual review recommended.",
                    "decision": "Suitable for a lower-grade role",
                    "justification": "Basic extraction completed, full AI screening unavailable"
                },
                "record_management": {
                    "screened_at_utc": datetime.utcnow().isoformat() + "Z",
                    "screened_by": "Senior Talent Acquisition Partner",
                    "tags": ["fallback_screening", "manual_review_needed"]
                }
            }

        return self._structured_completion(
            prompt,
            fallback=fallback,
            system_instruction=json.dumps(system_instruction, ensure_ascii=False),
        )

    def build_boolean_search(self, persona: CandidatePersona) -> str:
        skills = persona.skills or ["PMO", "Mega Project", "Stakeholder Management"]
        title = persona.title.replace(" ", "")
        skill_terms = " OR ".join(f'"{skill}"' for skill in skills)
        location = f" (\"{persona.location}\")" if persona.location else ""
        seniority = f" (\"{persona.seniority}\")" if persona.seniority else ""
        return f"(\"{persona.title}\" OR {title}) AND ({skill_terms}){location}{seniority}"

    def synthesise_candidate_profiles(self, persona: CandidatePersona, count: int = 5) -> List[Dict[str, Any]]:
        """Generate realistic candidate profiles using AI based on the persona criteria."""

        def fallback() -> List[Dict[str, Any]]:
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

        # Build a detailed prompt for AI-powered candidate profile generation
        persona_context = {
            "title": persona.title,
            "location": persona.location,
            "skills": persona.skills,
            "seniority": persona.seniority,
            "count": count,
        }

        prompt = f"""Generate {count} realistic candidate profiles matching this persona:

Title: {persona.title}
Location: {persona.location or 'Any'}
Skills: {', '.join(persona.skills) if persona.skills else 'Not specified'}
Seniority: {persona.seniority or 'Not specified'}

For each candidate, provide:
- name: A realistic full name
- title: Current job title (matching the persona)
- location: City/region
- platform: "LinkedIn"
- profile_url: Realistic LinkedIn URL format
- summary: 1-2 sentence professional summary highlighting relevant experience
- quality_score: Match quality score (0-100)
- company: Current or recent employer (realistic company name in the industry)

Return a JSON array of {count} candidate objects with these fields.

Requirements:
- Names should be diverse and realistic
- Companies should be real or realistic-sounding firms in construction/engineering/infrastructure
- Summaries should be specific and credible
- Quality scores should range from 65-95 based on fit
- LinkedIn URLs should follow pattern: https://linkedin.com/in/firstname-lastname-randomid"""

        return self._structured_completion(
            prompt,
            fallback=fallback,
            system_instruction="Generate realistic candidate profiles for recruitment sourcing. Return only valid JSON array.",
        )

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
