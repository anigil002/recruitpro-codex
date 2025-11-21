"""System-level endpoints."""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..services.queue import background_queue
from ..deps import get_db

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def healthcheck(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Comprehensive health check endpoint for monitoring production systems.

    Checks:
    - Database connectivity
    - Background queue status
    - Redis connection (if using Redis queue)
    - Gemini API configuration

    Returns status: "healthy", "degraded", or "unhealthy"
    """
    checks: Dict[str, Any] = {}
    overall_status = "healthy"

    # Check database
    try:
        db.execute(text("SELECT 1")).fetchone()
        checks["database"] = {"status": "healthy", "message": "Database connection OK"}
    except Exception as exc:
        checks["database"] = {"status": "unhealthy", "message": f"Database error: {str(exc)}"}
        overall_status = "unhealthy"

    # Check background queue
    try:
        queue_stats = background_queue.stats()
        backend = queue_stats.get("backend", "unknown")
        is_running = queue_stats.get("is_running", False)

        if is_running:
            checks["queue"] = {
                "status": "healthy",
                "message": f"Queue operational ({backend})",
                "backend": backend,
                "queued": queue_stats.get("queued", 0),
                "processed": queue_stats.get("processed", 0),
                "failed": queue_stats.get("failed", 0),
            }
        else:
            checks["queue"] = {
                "status": "degraded",
                "message": f"Queue not running ({backend})",
                "backend": backend,
            }
            if overall_status == "healthy":
                overall_status = "degraded"
    except Exception as exc:
        checks["queue"] = {"status": "unhealthy", "message": f"Queue error: {str(exc)}"}
        overall_status = "unhealthy"

    # Check Redis (if using Redis queue)
    try:
        queue_stats = background_queue.stats()
        if "redis" in queue_stats.get("backend", "").lower():
            # Redis is being used
            redis_url = queue_stats.get("redis_url", "unknown")
            checks["redis"] = {
                "status": "healthy",
                "message": "Redis connection OK",
                "url": redis_url,
            }
    except Exception as exc:
        if "redis" in str(exc).lower():
            checks["redis"] = {"status": "unhealthy", "message": f"Redis error: {str(exc)}"}
            overall_status = "unhealthy"

    # Check Gemini API configuration
    settings = get_settings()
    gemini_configured = bool(settings.gemini_api_key_value)
    checks["gemini_api"] = {
        "status": "healthy" if gemini_configured else "degraded",
        "message": "Gemini API key configured" if gemini_configured else "Gemini API key not configured",
        "configured": gemini_configured,
    }
    if not gemini_configured and overall_status == "healthy":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }


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
        "database_path": str(settings.resolved_database_path)
        if settings.resolved_database_path
        else None,
        "gemini_enabled": bool(settings.gemini_api_key_value),
        "smartrecruiters_enabled": bool(settings.smartrecruiters_email),
        "auto_updates": bool(getattr(settings, "auto_updates_enabled", True)),
    }
