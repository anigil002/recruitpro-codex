"""Structured JSON migration helpers for RecruitPro."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ..models import Candidate, Position, Project, ProjectDocument
from ..utils.security import generate_id


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value)
        except (ValueError, OSError):
            return None
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _coerce_int(value: Any, default: int | None = 0) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _ensure_list(value: Any) -> List[Any] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    return [value]


def apply_structured_json_migration(
    db: Session,
    payload: Dict[str, Any],
    *,
    current_user,
) -> Dict[str, Any]:
    """Import the supported objects from a structured JSON payload.

    The importer understands the keys ``projects``, ``positions``, ``candidates``
    and ``documents``. Each key should contain a list of dictionaries that map to
    the respective SQLAlchemy models. Missing optional fields are ignored and
    sensible defaults are applied where required so that legacy exports can be
    ingested without extensive preprocessing on the operator's side.
    """

    summary: Dict[str, Any] = {
        "items_total": 0,
        "items_success": 0,
        "items_failed": 0,
        "projects": {"created": 0, "updated": 0},
        "positions": {"created": 0, "updated": 0},
        "candidates": {"created": 0, "updated": 0},
        "documents": {"created": 0, "updated": 0},
        "errors": [],
    }

    def record_error(item_type: str, identifier: str | None, message: str) -> None:
        summary["items_failed"] += 1
        summary["errors"].append(
            {"item_type": item_type, "identifier": identifier, "error": message}
        )

    def ensure_project_exists(project_id: str) -> Project:
        project = db.get(Project, project_id)
        if not project:
            raise ValueError(f"Unknown project_id '{project_id}' referenced in import")
        return project

    projects = payload.get("projects") or []
    if not isinstance(projects, list):
        raise ValueError("The 'projects' field must be a list when provided.")

    for entry in projects:
        summary["items_total"] += 1
        if not isinstance(entry, dict):
            record_error("project", None, "Project entry must be an object")
            continue
        try:
            project_id = (entry.get("project_id") or "").strip() or generate_id()
            project = db.get(Project, project_id)
            created = False
            if not project:
                created = True
                created_at = _coerce_datetime(entry.get("created_at")) or datetime.utcnow()
                project = Project(
                    project_id=project_id,
                    name=(entry.get("name") or "Untitled Project").strip() or "Untitled Project",
                    sector=entry.get("sector"),
                    location_region=entry.get("location_region"),
                    summary=entry.get("summary"),
                    client=entry.get("client"),
                    status=entry.get("status") or "active",
                    priority=entry.get("priority") or "medium",
                    department=entry.get("department"),
                    tags=entry.get("tags") if isinstance(entry.get("tags"), list) else _ensure_list(entry.get("tags")) or [],
                    team_members=entry.get("team_members")
                    if isinstance(entry.get("team_members"), list)
                    else _ensure_list(entry.get("team_members"))
                    or [],
                    target_hires=_coerce_int(entry.get("target_hires"), 0),
                    hires_count=_coerce_int(entry.get("hires_count"), 0),
                    research_done=_coerce_int(entry.get("research_done"), 0),
                    research_status=entry.get("research_status"),
                    created_by=(entry.get("created_by") or current_user.user_id),
                    created_at=created_at,
                )
            else:
                for field in (
                    "name",
                    "sector",
                    "location_region",
                    "summary",
                    "client",
                    "status",
                    "priority",
                    "department",
                    "research_status",
                ):
                    if entry.get(field) is not None:
                        setattr(project, field, entry.get(field))
                if entry.get("tags") is not None:
                    project.tags = (
                        entry.get("tags")
                        if isinstance(entry.get("tags"), list)
                        else _ensure_list(entry.get("tags"))
                    )
                if entry.get("team_members") is not None:
                    project.team_members = (
                        entry.get("team_members")
                        if isinstance(entry.get("team_members"), list)
                        else _ensure_list(entry.get("team_members"))
                    )
                if entry.get("target_hires") is not None:
                    project.target_hires = _coerce_int(entry.get("target_hires"), project.target_hires)
                if entry.get("hires_count") is not None:
                    project.hires_count = _coerce_int(entry.get("hires_count"), project.hires_count)
                if entry.get("research_done") is not None:
                    project.research_done = _coerce_int(entry.get("research_done"), project.research_done)
                created = False
            db.add(project)
            summary["items_success"] += 1
            summary["projects"]["created" if created else "updated"] += 1
        except ValueError as error:
            record_error("project", entry.get("project_id") or entry.get("name"), str(error))

    positions = payload.get("positions") or []
    if not isinstance(positions, list):
        raise ValueError("The 'positions' field must be a list when provided.")

    for entry in positions:
        summary["items_total"] += 1
        if not isinstance(entry, dict):
            record_error("position", None, "Position entry must be an object")
            continue
        try:
            project_id = (entry.get("project_id") or "").strip()
            if not project_id and entry.get("project_name"):
                match = (
                    db.query(Project)
                    .filter(Project.name == entry.get("project_name"))
                    .first()
                )
                if match:
                    project_id = match.project_id
            if not project_id:
                raise ValueError("Positions require a project_id or project_name reference")
            ensure_project_exists(project_id)

            position_id = (entry.get("position_id") or "").strip() or generate_id()
            position = db.get(Position, position_id)
            created = False
            created_at = _coerce_datetime(entry.get("created_at"))
            if not position:
                created = True
                position = Position(
                    position_id=position_id,
                    project_id=project_id,
                    title=(entry.get("title") or "New Role").strip() or "New Role",
                    department=entry.get("department"),
                    experience=entry.get("experience"),
                    responsibilities=entry.get("responsibilities")
                    if isinstance(entry.get("responsibilities"), list)
                    else _ensure_list(entry.get("responsibilities")),
                    requirements=entry.get("requirements")
                    if isinstance(entry.get("requirements"), list)
                    else _ensure_list(entry.get("requirements")),
                    location=entry.get("location"),
                    description=entry.get("description"),
                    status=entry.get("status") or "draft",
                    openings=_coerce_int(entry.get("openings"), 1),
                    applicants_count=_coerce_int(entry.get("applicants_count"), 0),
                    created_at=created_at or datetime.utcnow(),
                )
            else:
                for field in (
                    "title",
                    "department",
                    "experience",
                    "location",
                    "description",
                    "status",
                ):
                    if entry.get(field) is not None:
                        setattr(position, field, entry.get(field))
                if entry.get("responsibilities") is not None:
                    position.responsibilities = (
                        entry.get("responsibilities")
                        if isinstance(entry.get("responsibilities"), list)
                        else _ensure_list(entry.get("responsibilities"))
                    )
                if entry.get("requirements") is not None:
                    position.requirements = (
                        entry.get("requirements")
                        if isinstance(entry.get("requirements"), list)
                        else _ensure_list(entry.get("requirements"))
                    )
                if entry.get("status") is not None:
                    position.status = entry.get("status")
                if entry.get("openings") is not None:
                    position.openings = _coerce_int(entry.get("openings"), position.openings)
                if entry.get("applicants_count") is not None:
                    position.applicants_count = _coerce_int(
                        entry.get("applicants_count"), position.applicants_count
                    )
                if created_at:
                    position.created_at = created_at
            db.add(position)
            summary["items_success"] += 1
            summary["positions"]["created" if created else "updated"] += 1
        except ValueError as error:
            record_error("position", entry.get("position_id") or entry.get("title"), str(error))

    candidates = payload.get("candidates") or []
    if not isinstance(candidates, list):
        raise ValueError("The 'candidates' field must be a list when provided.")

    for entry in candidates:
        summary["items_total"] += 1
        if not isinstance(entry, dict):
            record_error("candidate", None, "Candidate entry must be an object")
            continue
        try:
            candidate_id = (entry.get("candidate_id") or "").strip() or generate_id()
            candidate = db.get(Candidate, candidate_id)
            created = False
            created_at = _coerce_datetime(entry.get("created_at"))
            if not candidate:
                created = True
                candidate = Candidate(
                    candidate_id=candidate_id,
                    project_id=entry.get("project_id"),
                    position_id=entry.get("position_id"),
                    name=(entry.get("name") or "New Candidate").strip() or "New Candidate",
                    email=entry.get("email"),
                    phone=entry.get("phone"),
                    source=entry.get("source") or "migration",
                    status=entry.get("status") or "new",
                    rating=_coerce_int(entry.get("rating"), None),
                    resume_url=entry.get("resume_url"),
                    tags=entry.get("tags") if isinstance(entry.get("tags"), list) else _ensure_list(entry.get("tags")),
                    ai_score=entry.get("ai_score"),
                    created_at=created_at or datetime.utcnow(),
                )
            else:
                for field in (
                    "project_id",
                    "position_id",
                    "name",
                    "email",
                    "phone",
                    "source",
                    "status",
                    "resume_url",
                ):
                    if entry.get(field) is not None:
                        setattr(candidate, field, entry.get(field))
                if entry.get("rating") is not None:
                    candidate.rating = _coerce_int(entry.get("rating"), candidate.rating or 0)
                if entry.get("tags") is not None:
                    candidate.tags = (
                        entry.get("tags")
                        if isinstance(entry.get("tags"), list)
                        else _ensure_list(entry.get("tags"))
                    )
                if entry.get("ai_score") is not None:
                    candidate.ai_score = entry.get("ai_score")
                if created_at:
                    candidate.created_at = created_at
            if not candidate.source:
                candidate.source = "migration"
            db.add(candidate)
            summary["items_success"] += 1
            summary["candidates"]["created" if created else "updated"] += 1
        except ValueError as error:
            record_error("candidate", entry.get("candidate_id") or entry.get("email"), str(error))

    documents = payload.get("documents") or []
    if not isinstance(documents, list):
        raise ValueError("The 'documents' field must be a list when provided.")

    for entry in documents:
        summary["items_total"] += 1
        if not isinstance(entry, dict):
            record_error("document", None, "Document entry must be an object")
            continue
        try:
            project_id = (entry.get("project_id") or "").strip()
            if not project_id:
                raise ValueError("Documents require an associated project_id")
            ensure_project_exists(project_id)

            file_url = (entry.get("file_url") or entry.get("url") or "").strip()
            if not file_url:
                raise ValueError("Documents require a file_url for retrieval")

            doc_id = (entry.get("doc_id") or entry.get("document_id") or "").strip() or generate_id()
            document = db.get(ProjectDocument, doc_id)
            created = False
            uploaded_at = _coerce_datetime(entry.get("uploaded_at")) or datetime.utcnow()
            if not document:
                created = True
                document = ProjectDocument(
                    doc_id=doc_id,
                    project_id=project_id,
                    filename=(entry.get("filename") or entry.get("name") or "Attachment").strip()
                    or "Attachment",
                    file_url=file_url,
                    mime_type=(entry.get("mime_type") or entry.get("content_type") or "application/octet-stream"),
                    uploaded_by=(entry.get("uploaded_by") or current_user.user_id),
                    uploaded_at=uploaded_at,
                )
            else:
                for field in ("filename", "mime_type", "uploaded_by"):
                    if entry.get(field) is not None:
                        setattr(document, field, entry.get(field))
                document.file_url = file_url
                document.project_id = project_id
                document.uploaded_at = uploaded_at
            db.add(document)
            summary["items_success"] += 1
            summary["documents"]["created" if created else "updated"] += 1
        except ValueError as error:
            record_error("document", entry.get("doc_id") or entry.get("filename"), str(error))

    # Ensure the session is aware of all pending work. This will raise if the
    # payload violates constraints, allowing the API layer to surface the error.
    if summary["items_success"]:
        db.flush()

    summary["items_total"] = summary["items_success"] + summary["items_failed"]
    return summary
