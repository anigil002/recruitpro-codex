"""RecruitPro FastAPI application."""

import json
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .config import get_settings
from .deps import get_db
from .routers import (
    activity,
    admin,
    ai,
    auth,
    candidates,
    documents,
    interviews,
    projects,
    sourcing,
    system,
)
from .models import (
    ActivityFeed,
    AIJob,
    Candidate,
    Position,
    Project,
    ProjectDocument,
    ProjectMarketResearch,
    SourcingJob,
    SourcingResult,
    User,
)
from .utils.security import decode_token

settings = get_settings()

app = FastAPI(title=settings.app_name)

if settings.cors_allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With", "Origin"],
    )

templates = Jinja2Templates(directory="templates")

try:
    from .utils.storage import ensure_storage_dir

    storage_dir = ensure_storage_dir()
    storage_path = storage_dir
except Exception:  # pragma: no cover - fallback if storage helper missing
    storage_path = settings.storage_path

app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")


def _user_payload(user: User) -> dict[str, Any]:
    initials_source = "".join(part[0] for part in (user.name or "").split() if part)
    if not initials_source and user.email:
        initials_source = user.email[0]
    initials = initials_source.upper()[:2] or "U"
    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "initials": initials,
    }


def _resolve_user(
    db: Session, token: Optional[str]
) -> tuple[Optional[User], Optional[dict[str, Any]], Optional[str]]:
    if not token:
        return None, None, None
    user_id = decode_token(token)
    if not user_id:
        return None, None, "Invalid access token."
    user = db.get(User, user_id)
    if not user:
        return None, None, "User not found."
    return user, _user_payload(user), None


def _build_project_overview(db: Session, project: Project) -> dict[str, Any]:
    positions = (
        db.query(Position)
        .filter(Position.project_id == project.project_id)
        .order_by(Position.created_at.desc())
        .all()
    )
    position_payload: list[dict[str, Any]] = []
    position_stats = {"total": len(positions), "open": 0, "closed": 0, "draft": 0, "other": 0}
    for pos in positions:
        status_key = (pos.status or "").lower()
        if status_key in {"open", "closed", "draft"}:
            position_stats[status_key] += 1
        else:
            position_stats["other"] += 1
        position_payload.append(
            {
                "position_id": pos.position_id,
                "title": pos.title,
                "status": pos.status or "unspecified",
                "department": pos.department,
                "location": pos.location,
                "openings": pos.openings or 0,
                "applicants_count": pos.applicants_count or 0,
                "created_at": pos.created_at,
            }
        )

    candidate_query = db.query(Candidate).filter(Candidate.project_id == project.project_id)
    candidate_total = candidate_query.count()
    status_rows = (
        candidate_query.with_entities(func.coalesce(Candidate.status, ""), func.count(Candidate.candidate_id))
        .group_by(Candidate.status)
        .all()
    )
    candidate_by_status = []
    for status, count in status_rows:
        label = status if status else "unspecified"
        candidate_by_status.append({"status": label, "count": count})
    candidate_by_status.sort(key=lambda item: item["status"])

    recent_candidates = [
        {
            "candidate_id": cand.candidate_id,
            "name": cand.name,
            "status": cand.status or "unspecified",
            "source": cand.source,
            "created_at": cand.created_at,
        }
        for cand in candidate_query.order_by(Candidate.created_at.desc()).limit(5)
    ]

    documents = (
        db.query(ProjectDocument)
        .filter(ProjectDocument.project_id == project.project_id)
        .order_by(ProjectDocument.uploaded_at.desc())
        .limit(5)
        .all()
    )
    document_payload = [
        {
            "doc_id": doc.doc_id,
            "filename": doc.filename,
            "mime_type": doc.mime_type,
            "uploaded_at": doc.uploaded_at,
            "url": f"/storage/{doc.file_url}" if doc.file_url else None,
        }
        for doc in documents
    ]

    activity = (
        db.query(ActivityFeed)
        .filter(ActivityFeed.project_id == project.project_id)
        .order_by(ActivityFeed.created_at.desc())
        .limit(5)
        .all()
    )
    activity_payload = [
        {
            "activity_id": item.activity_id,
            "message": item.message,
            "event_type": item.event_type,
            "created_at": item.created_at,
        }
        for item in activity
    ]

    research = (
        db.query(ProjectMarketResearch)
        .filter(ProjectMarketResearch.project_id == project.project_id)
        .order_by(ProjectMarketResearch.completed_at.desc().nullslast(), ProjectMarketResearch.started_at.desc())
        .first()
    )
    research_payload = None
    if research:
        findings = research.findings or []
        if isinstance(findings, dict):
            findings = findings.get("items") or findings.get("data") or []
        research_payload = {
            "status": research.status,
            "completed_at": research.completed_at or research.started_at,
            "region": research.region,
            "window": research.window,
            "findings": findings[:5] if isinstance(findings, list) else [],
            "sources": research.sources or [],
        }

    screening_job = (
        db.query(AIJob)
        .filter(AIJob.project_id == project.project_id, AIJob.job_type == "ai_screening")
        .order_by(AIJob.created_at.desc())
        .first()
    )
    screening_payload = None
    if screening_job:
        screening_payload = {
            "status": screening_job.status,
            "created_at": screening_job.created_at,
            "updated_at": screening_job.updated_at,
        }

    project_payload = {
        "project_id": project.project_id,
        "name": project.name,
        "client": project.client,
        "status": project.status or "unspecified",
        "summary": project.summary,
        "sector": project.sector,
        "location_region": project.location_region,
        "tags": sorted(project.tags or []),
        "team_members": sorted(project.team_members or []),
        "target_hires": project.target_hires or 0,
        "hires_count": project.hires_count or 0,
        "research_status": project.research_status,
        "created_at": project.created_at,
    }

    return {
        "project": project_payload,
        "positions": position_payload,
        "position_stats": position_stats,
        "candidate_summary": {
            "total": candidate_total,
            "by_status": candidate_by_status,
            "recent": recent_candidates,
        },
        "documents": document_payload,
        "recent_activity": activity_payload,
        "market_research": research_payload,
        "ai_screening": screening_payload,
    }


def _build_sourcing_overview(
    db: Session, user: User, project_id: Optional[str] = None
) -> dict[str, Any]:
    job_query = (
        db.query(SourcingJob)
        .join(Project, SourcingJob.project_id == Project.project_id)
        .filter(Project.created_by == user.user_id)
        .order_by(SourcingJob.created_at.desc())
    )
    if project_id:
        job_query = job_query.filter(SourcingJob.project_id == project_id)
    jobs = job_query.all()

    job_payload: list[dict[str, Any]] = []
    active_jobs = 0
    total_profiles = 0
    tracked_projects: set[str] = set()
    for job in jobs:
        project = db.get(Project, job.project_id)
        position = db.get(Position, job.position_id) if job.position_id else None
        status = job.status or "pending"
        if status not in {"completed", "failed"}:
            active_jobs += 1
        total_profiles += job.found_count or 0
        if project:
            tracked_projects.add(project.project_id)
        job_payload.append(
            {
                "sourcing_job_id": job.sourcing_job_id,
                "project_name": project.name if project else "Unknown project",
                "position_title": position.title if position else "Unassigned role",
                "status": status,
                "progress": job.progress or 0,
                "found_count": job.found_count or 0,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }
        )

    result_query = (
        db.query(SourcingResult)
        .join(SourcingJob, SourcingResult.sourcing_job_id == SourcingJob.sourcing_job_id)
        .join(Project, SourcingJob.project_id == Project.project_id)
        .filter(Project.created_by == user.user_id)
        .order_by(SourcingResult.created_at.desc())
    )
    if project_id:
        result_query = result_query.filter(SourcingJob.project_id == project_id)
    results = result_query.limit(12).all()
    result_payload = [
        {
            "result_id": result.result_id,
            "name": result.name,
            "title": result.title,
            "company": result.company,
            "location": result.location,
            "profile_url": result.profile_url,
            "quality_score": result.quality_score,
            "created_at": result.created_at,
        }
        for result in results
    ]

    return {
        "summary": {
            "total_jobs": len(jobs),
            "active_jobs": active_jobs,
            "total_profiles": total_profiles,
            "tracked_projects": len(tracked_projects),
        },
        "jobs": job_payload,
        "results": result_payload,
    }

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(candidates.router)
app.include_router(documents.router)
app.include_router(activity.router)
app.include_router(ai.router)
app.include_router(sourcing.router)
app.include_router(interviews.router)
app.include_router(admin.router)
app.include_router(system.router)


@app.get("/")
def index() -> RedirectResponse:
    """Provide a friendly landing page by redirecting to the UI shell."""

    return RedirectResponse(url="/app", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/doc")
def docs_alias() -> RedirectResponse:
    """Redirect legacy `/doc` requests to FastAPI's `/docs` UI."""

    return RedirectResponse(url="/docs", status_code=status.HTTP_308_PERMANENT_REDIRECT)


@app.get("/app", response_class=HTMLResponse)
async def application_shell(request: Request) -> HTMLResponse:
    """Serve the interactive RecruitPro console."""

    return templates.TemplateResponse("recruitpro_ats.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Render the RecruitPro login experience."""

    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/candidate-profile", response_class=HTMLResponse)
async def candidate_profile_page(
    request: Request,
    candidate_id: Optional[str] = None,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render a candidate profile populated with live database data."""

    context: dict[str, object] = {
        "request": request,
        "candidate": None,
        "project": None,
        "position": None,
    }

    if not candidate_id:
        return templates.TemplateResponse("candidate_profile.html", context)

    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    project: Optional[Project] = db.get(Project, candidate.project_id) if candidate.project_id else None
    position: Optional[Position] = db.get(Position, candidate.position_id) if candidate.position_id else None

    user_id = decode_token(token) if token else None
    if token and not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if user_id and project and project.created_by != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view candidate")

    candidate_data = {
        "candidate_id": candidate.candidate_id,
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "source": candidate.source,
        "status": candidate.status,
        "rating": candidate.rating,
        "resume_url": candidate.resume_url,
        "tags": candidate.tags or [],
        "ai_score": candidate.ai_score,
        "ai_score_json": json.dumps(candidate.ai_score, indent=2) if candidate.ai_score else None,
        "created_at": candidate.created_at,
    }

    project_data: Optional[dict[str, Any]] = None
    if project:
        project_data = {
            "project_id": project.project_id,
            "name": project.name,
            "client": project.client,
            "status": project.status,
        }

    position_data: Optional[dict[str, Any]] = None
    if position:
        position_data = {
            "position_id": position.position_id,
            "title": position.title,
            "status": position.status,
        }

    context.update(
        {
            "candidate": candidate_data,
            "project": project_data,
            "position": position_data,
        }
    )
    return templates.TemplateResponse("candidate_profile.html", context)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    """Render the workspace settings configuration UI."""

    sidebar = {
        "logo_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuC1J7UyLIViqxSyACOj8r849gKCUxlXYhUoJzEPigDkrZrbTnpsbhrACpejUnyYK6Ec_01VMtmnR7HmFzI5uclry4cYgWo9ECs4m1Lrot4i24aa9HaRaQ4P9njXkzBgSX_DBdqPqROdPX9mAun8S9oQQG3xgY4WjAj_EuZANnFsAo00q5hkvrENCWOtcycFa37bqnznIWTyTu8boN53lb4heHut2Zzi4Bd_wKPg-vjsR8mVfVnVhrfdDfihlo7aMo00Ffg1XMG3UX0",
        "workspace_name": settings.app_name,
        "workspace_context": "Workspace Settings",
        "menu": [
            {"icon": "account_circle", "label": "Profile", "href": "#", "active": False},
            {"icon": "notifications", "label": "Notifications", "href": "#", "active": False},
            {
                "icon": "key",
                "label": "API Keys",
                "href": "#",
                "active": True,
                "icon_filled": True,
            },
            {"icon": "extension", "label": "Integrations", "href": "#", "active": False},
            {"icon": "database", "label": "Data & Storage", "href": "#", "active": False},
        ],
        "secondary_menu": [
            {"icon": "help_outline", "label": "Help Center", "href": "#"},
            {"icon": "logout", "label": "Logout", "href": "#"},
        ],
    }

    gemini = {
        "configured": bool(settings.gemini_api_key_value),
        "value": settings.gemini_api_key_value,
        "learn_more_url": "https://ai.google.dev/gemini-api/docs/api-key",
    }

    google = {
        "configured": bool(settings.google_search_api_key_value and settings.google_custom_search_engine_id),
        "value": settings.google_search_api_key_value,
        "search_engine_id": settings.google_custom_search_engine_id or "",
        "learn_more_url": "https://developers.google.com/custom-search/v1/overview",
    }

    context = {
        "request": request,
        "sidebar": sidebar,
        "gemini": gemini,
        "google": google,
    }

    return templates.TemplateResponse("settings.html", context)


@app.get("/project-overview", response_class=HTMLResponse)
async def project_overview_page(
    request: Request,
    project_id: Optional[str] = None,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render a live overview for a single project."""

    context: dict[str, Any] = {
        "request": request,
        "user": None,
        "token": token,
        "project": None,
        "positions": [],
        "position_stats": {"total": 0, "open": 0, "closed": 0, "draft": 0, "other": 0},
        "candidate_summary": {"total": 0, "by_status": [], "recent": []},
        "documents": [],
        "recent_activity": [],
        "market_research": None,
        "ai_screening": None,
        "error": None,
    }

    user, user_payload, user_error = _resolve_user(db, token)
    if user_payload:
        context["user"] = user_payload
    if user_error:
        context["error"] = user_error

    if not project_id:
        context["error"] = context["error"] or "Provide a project_id query parameter to view a project."
        return templates.TemplateResponse("project_page.html", context)

    if not user:
        context["error"] = context["error"] or "A valid token is required to load project information."
        return templates.TemplateResponse("project_page.html", context)

    project = db.get(Project, project_id)
    if not project or project.created_by != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    context.update(_build_project_overview(db, project))
    return templates.TemplateResponse("project_page.html", context)


@app.get("/project-positions", response_class=HTMLResponse)
async def project_positions_page(
    request: Request,
    project_id: Optional[str] = None,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render a position inventory for a project."""

    context: dict[str, Any] = {
        "request": request,
        "user": None,
        "token": token,
        "project": None,
        "positions": [],
        "position_stats": {"total": 0, "open": 0, "closed": 0, "draft": 0, "other": 0},
        "candidate_summary": {"total": 0, "by_status": [], "recent": []},
        "error": None,
    }

    user, user_payload, user_error = _resolve_user(db, token)
    if user_payload:
        context["user"] = user_payload
    if user_error:
        context["error"] = user_error

    if not project_id:
        context["error"] = context["error"] or "Provide a project_id query parameter to list positions."
        return templates.TemplateResponse("project_positions.html", context)

    if not user:
        context["error"] = context["error"] or "A valid token is required to view project positions."
        return templates.TemplateResponse("project_positions.html", context)

    project = db.get(Project, project_id)
    if not project or project.created_by != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    context.update(_build_project_overview(db, project))
    return templates.TemplateResponse("project_positions.html", context)


@app.get("/ai/sourcing-overview", response_class=HTMLResponse)
async def ai_sourcing_overview_page(
    request: Request,
    token: Optional[str] = None,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render AI sourcing activity connected to live data."""

    context: dict[str, Any] = {
        "request": request,
        "user": None,
        "token": token,
        "summary": {"total_jobs": 0, "active_jobs": 0, "total_profiles": 0, "tracked_projects": 0},
        "jobs": [],
        "results": [],
        "projects": [],
        "selected_project_id": project_id,
        "error": None,
    }

    user, user_payload, user_error = _resolve_user(db, token)
    if user_payload:
        context["user"] = user_payload
    if user_error:
        context["error"] = user_error

    if not user:
        context["error"] = context["error"] or "Sign in with a token to review AI sourcing runs."
        return templates.TemplateResponse("ai_sourcing_overview.html", context)

    if project_id:
        project = db.get(Project, project_id)
        if not project or project.created_by != user.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    context.update(_build_sourcing_overview(db, user, project_id))
    context["projects"] = [
        {"project_id": proj.project_id, "name": proj.name}
        for proj in db.query(Project).filter(Project.created_by == user.user_id).order_by(Project.name).all()
    ]
    return templates.TemplateResponse("ai_sourcing_overview.html", context)
