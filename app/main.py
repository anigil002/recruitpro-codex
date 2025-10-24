"""RecruitPro FastAPI application."""

import json
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
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
from .models import Candidate, Position, Project
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
def index():
    return {"status": "ok", "message": "RecruitPro backend is running."}


@app.get("/app", response_class=HTMLResponse)
async def application_shell(request: Request) -> HTMLResponse:
    """Serve the interactive RecruitPro console."""

    return templates.TemplateResponse("recruitpro_ats.html", {"request": request})


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
