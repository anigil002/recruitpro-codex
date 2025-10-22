"""System-level endpoints."""

from datetime import datetime

from fastapi import APIRouter

from ..config import get_settings

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def healthcheck() -> dict:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/version")
def version() -> dict:
    settings = get_settings()
    return {"app": settings.app_name, "version": "0.1.0"}
