"""RecruitPro FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import get_settings
from .database import Base, engine
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

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RecruitPro ATS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
settings = get_settings()

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
