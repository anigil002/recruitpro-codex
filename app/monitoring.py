"""
Monitoring & Observability

This module integrates monitoring and error tracking for production deployments.

Features:
- Sentry for error tracking and performance monitoring
- Prometheus metrics for application monitoring
- Custom metrics for business logic
"""

import logging
from typing import Callable

import sentry_sdk
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from .config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


# Prometheus Metrics
# ==================

# HTTP Requests
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

# Background Jobs
jobs_enqueued_total = Counter(
    "jobs_enqueued_total",
    "Total jobs enqueued",
    ["queue", "task"]
)

jobs_completed_total = Counter(
    "jobs_completed_total",
    "Total jobs completed",
    ["queue", "task", "status"]
)

jobs_duration_seconds = Histogram(
    "jobs_duration_seconds",
    "Job execution duration in seconds",
    ["queue", "task"]
)

# Database
db_connections_active = Gauge(
    "db_connections_active",
    "Active database connections"
)

db_queries_total = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation"]
)

# Business Metrics
candidates_created_total = Counter(
    "candidates_created_total",
    "Total candidates created"
)

screenings_performed_total = Counter(
    "screenings_performed_total",
    "Total candidate screenings performed"
)

ai_requests_total = Counter(
    "ai_requests_total",
    "Total AI API requests",
    ["feature", "status"]
)


def init_sentry():
    """
    Initialize Sentry for error tracking and performance monitoring.

    Call this function at application startup.
    """
    if not settings.sentry_dsn:
        logger.info("Sentry DSN not configured, skipping Sentry initialization")
        return

    try:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration(),
            ],
            # Enable performance monitoring
            _experiments={
                "profiles_sample_rate": 0.1,
            },
            # Send user context
            send_default_pii=False,
            # Release tracking
            release=f"recruitpro@{get_app_version()}",
        )

        logger.info(
            f"Sentry initialized: env={settings.sentry_environment}, "
            f"sample_rate={settings.sentry_traces_sample_rate}"
        )
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def get_app_version() -> str:
    """Get application version from package metadata."""
    try:
        from importlib.metadata import version
        return version("recruitpro")
    except Exception:
        return "0.1.0"


def get_prometheus_metrics() -> bytes:
    """
    Get current Prometheus metrics.

    Returns:
        bytes: Prometheus metrics in text format
    """
    return generate_latest()


# Monitoring Decorators
# =====================

def track_db_query(operation: str) -> Callable:
    """
    Decorator to track database query metrics.

    Usage:
        @track_db_query("select")
        def get_user(user_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            db_queries_total.labels(operation=operation).inc()
            return func(*args, **kwargs)
        return wrapper
    return decorator


def track_ai_request(feature: str) -> Callable:
    """
    Decorator to track AI request metrics.

    Usage:
        @track_ai_request("cv_screening")
        def screen_candidate(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                ai_requests_total.labels(feature=feature, status="success").inc()
                return result
            except Exception as e:
                ai_requests_total.labels(feature=feature, status="error").inc()
                raise
        return wrapper
    return decorator


# Health Check Helpers
# ====================

def get_system_health() -> dict:
    """
    Get overall system health status.

    Returns:
        Dict with health information:
        {
            'status': 'healthy' | 'degraded' | 'unhealthy',
            'checks': {
                'database': {'status': 'up', 'latency_ms': 10},
                'redis': {'status': 'up', 'latency_ms': 5},
                'queue': {'status': 'up', 'pending_jobs': 42},
            }
        }
    """
    import time
    from sqlalchemy import text

    from .database import engine
    from .queue import get_queue_stats, redis_conn

    checks = {}

    # Database check
    try:
        start = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        checks["database"] = {"status": "up", "latency_ms": round(latency, 2)}
    except Exception as e:
        checks["database"] = {"status": "down", "error": str(e)}

    # Redis check
    try:
        start = time.time()
        redis_conn.ping()
        latency = (time.time() - start) * 1000
        checks["redis"] = {"status": "up", "latency_ms": round(latency, 2)}
    except Exception as e:
        checks["redis"] = {"status": "down", "error": str(e)}

    # Queue check
    try:
        stats = get_queue_stats()
        total_pending = sum(q["queued"] for q in stats.values())
        checks["queue"] = {
            "status": "up",
            "pending_jobs": total_pending,
            "queues": stats,
        }
    except Exception as e:
        checks["queue"] = {"status": "down", "error": str(e)}

    # Determine overall status
    statuses = [check.get("status") for check in checks.values()]
    if all(s == "up" for s in statuses):
        overall_status = "healthy"
    elif any(s == "down" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "checks": checks,
        "version": get_app_version(),
        "environment": settings.environment,
    }
