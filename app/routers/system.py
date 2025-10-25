"""System-level endpoints."""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter

from ..config import get_settings
from ..services.queue import background_queue

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def healthcheck() -> dict:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/version")
def version() -> dict:
    settings = get_settings()
    return {"app": settings.app_name, "version": "0.1.0"}


@router.get("/queue/status")
def queue_status() -> Dict[str, object]:
    """Expose diagnostics for the in-process background queue."""

    return background_queue.stats()


@router.get("/system/config")
def system_config() -> Dict[str, object]:
    """Return a sanitized snapshot of runtime configuration for the desktop UI."""

    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "environment": getattr(settings, "environment", "production"),
        "storage_path": str(settings.storage_path),
        "gemini_enabled": bool(settings.gemini_api_key_value),
        "smartrecruiters_enabled": bool(settings.smartrecruiters_email),
        "auto_updates": bool(getattr(settings, "auto_updates_enabled", True)),
    }
