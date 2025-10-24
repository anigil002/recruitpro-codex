"""RecruitPro FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import get_settings
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
