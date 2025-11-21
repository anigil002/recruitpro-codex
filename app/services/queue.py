"""Production-ready background queue with Redis + RQ support and in-memory fallback."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Try to import Redis and RQ for production queue
try:
    import redis
    from rq import Queue as RQQueue
    from rq.job import Job as RQJob
    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore[assignment]
    RQQueue = None  # type: ignore[assignment, misc]
    RQJob = None  # type: ignore[assignment, misc]
    REDIS_AVAILABLE = False


class BackgroundQueue:
    """Very small thread-based job queue.

    The goal is to mimic the behaviour of RQ/Celery in a lightweight way so
    the rest of the codebase can enqueue background jobs.  Jobs are executed by
    a dedicated daemon thread.
    """

    def __init__(self) -> None:
        self._queue: "Queue[tuple[str, Dict[str, Any]]]" = Queue()
        self._handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self._thread: Optional[Thread] = None
        self._stop = Event()
        self._lock = Lock()
        self._processed: int = 0
        self._failed: int = 0
        self._last_job: Optional[Dict[str, Any]] = None
        self._last_error: Optional[str] = None
        self._last_updated: Optional[str] = None

    def register_handler(self, job_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            self._handlers[job_type] = handler

    def enqueue(self, job_type: str, payload: Dict[str, Any]) -> None:
        self._queue.put((job_type, payload))
        with self._lock:
            self._last_job = {
                "job_type": job_type,
                "payload": payload,
                "status": "queued",
            }
            self._last_updated = datetime.utcnow().isoformat()

    def registered_job_types(self) -> Dict[str, Callable[[Dict[str, Any]], None]]:
        """Return a copy of the registered job handlers."""

        with self._lock:
            return dict(self._handlers)

    def stats(self) -> Dict[str, Any]:
        """Expose diagnostic information for dashboards."""

        with self._lock:
            return {
                "queued": self._queue.qsize(),
                "handlers": sorted(self._handlers.keys()),
                "is_running": bool(self._thread and self._thread.is_alive()),
                "processed": self._processed,
                "failed": self._failed,
                "last_job": self._last_job.copy() if isinstance(self._last_job, dict) else self._last_job,
                "last_error": self._last_error,
                "last_updated": self._last_updated,
                "backend": "in-memory (thread-based)",
            }

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._thread = Thread(target=self._run, name="recruitpro-worker", daemon=True)
            self._thread.start()

    def shutdown(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                job_type, payload = self._queue.get(timeout=0.5)
            except Empty:
                continue
            handler = self._handlers.get(job_type)
            if not handler:
                logging.warning("No handler registered for job type %s", job_type)
                continue
            try:
                handler(payload)
                with self._lock:
                    self._processed += 1
                    self._last_job = {
                        "job_type": job_type,
                        "payload": payload,
                        "status": "completed",
                    }
                    self._last_error = None
                    self._last_updated = datetime.utcnow().isoformat()
            except Exception:  # pragma: no cover - logged for observability
                logging.exception("Background job %s failed", job_type)
                with self._lock:
                    self._failed += 1
                    self._last_job = {
                        "job_type": job_type,
                        "payload": payload,
                        "status": "failed",
                    }
                    self._last_error = "Unexpected error while processing job"
                    self._last_updated = datetime.utcnow().isoformat()
            finally:
                self._queue.task_done()


class RedisQueue:
    """Production-ready Redis + RQ based job queue with persistence."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis and RQ are not installed. Install with: pip install redis rq")

        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis_client: Optional[redis.Redis] = None
        self._queue: Optional[RQQueue] = None
        self._handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self._lock = Lock()
        self._connect()

    def _connect(self) -> None:
        """Connect to Redis and initialize RQ queue."""
        try:
            self._redis_client = redis.from_url(
                self._redis_url,
                socket_connect_timeout=5,
                socket_timeout=5,
                decode_responses=False,
            )
            # Test connection
            self._redis_client.ping()
            self._queue = RQQueue("recruitpro", connection=self._redis_client)
            logger.info(f"✓ Connected to Redis at {self._redis_url}")
        except Exception as exc:
            logger.error(f"Failed to connect to Redis: {exc}")
            raise RuntimeError(f"Redis connection failed: {exc}")

    def register_handler(self, job_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register a job handler. This is for compatibility with BackgroundQueue API."""
        with self._lock:
            self._handlers[job_type] = handler
            # Store handler in a global registry that workers can access
            _HANDLER_REGISTRY[job_type] = handler

    def enqueue(self, job_type: str, payload: Dict[str, Any]) -> None:
        """Enqueue a job for processing by RQ workers."""
        if not self._queue:
            raise RuntimeError("Redis queue not initialized")

        try:
            # Enqueue the job with the generic worker function
            job = self._queue.enqueue(
                _execute_job,
                job_type,
                payload,
                job_timeout="10m",  # 10 minute timeout for AI jobs
                result_ttl=86400,  # Keep results for 24 hours
                failure_ttl=604800,  # Keep failures for 7 days
            )
            logger.info(f"Enqueued {job_type} job: {job.id}")
        except Exception as exc:
            logger.error(f"Failed to enqueue {job_type} job: {exc}")
            raise

    def registered_job_types(self) -> Dict[str, Callable[[Dict[str, Any]], None]]:
        """Return a copy of the registered job handlers."""
        with self._lock:
            return dict(self._handlers)

    def stats(self) -> Dict[str, Any]:
        """Expose diagnostic information for dashboards."""
        if not self._queue or not self._redis_client:
            return {
                "queued": 0,
                "handlers": [],
                "is_running": False,
                "processed": 0,
                "failed": 0,
                "last_job": None,
                "last_error": "Queue not initialized",
                "last_updated": None,
                "backend": "redis (disconnected)",
            }

        try:
            queued_count = len(self._queue)
            started_count = len(self._queue.started_job_registry)
            finished_count = len(self._queue.finished_job_registry)
            failed_count = len(self._queue.failed_job_registry)

            return {
                "queued": queued_count,
                "started": started_count,
                "handlers": sorted(self._handlers.keys()),
                "is_running": True,
                "processed": finished_count,
                "failed": failed_count,
                "last_job": None,  # RQ doesn't track this easily
                "last_error": None,
                "last_updated": datetime.utcnow().isoformat(),
                "backend": "redis + rq",
                "redis_url": self._redis_url.split("@")[-1] if "@" in self._redis_url else self._redis_url,
            }
        except Exception as exc:
            logger.error(f"Failed to get queue stats: {exc}")
            return {
                "queued": 0,
                "handlers": sorted(self._handlers.keys()),
                "is_running": False,
                "processed": 0,
                "failed": 0,
                "last_job": None,
                "last_error": str(exc),
                "last_updated": datetime.utcnow().isoformat(),
                "backend": "redis (error)",
            }

    def start(self) -> None:
        """No-op for RedisQueue. Workers are started separately via `rq worker`."""
        logger.info("RedisQueue uses external RQ workers. Start workers with: rq worker recruitpro")

    def shutdown(self) -> None:
        """Close Redis connection."""
        if self._redis_client:
            self._redis_client.close()
            logger.info("Redis connection closed")


# Global handler registry for RQ workers
_HANDLER_REGISTRY: Dict[str, Callable[[Dict[str, Any]], None]] = {}


def _execute_job(job_type: str, payload: Dict[str, Any]) -> None:
    """Generic job executor called by RQ workers."""
    handler = _HANDLER_REGISTRY.get(job_type)
    if not handler:
        logger.error(f"No handler registered for job type: {job_type}")
        raise RuntimeError(f"No handler registered for job type: {job_type}")

    logger.info(f"Executing {job_type} job with payload: {payload}")
    try:
        handler(payload)
        logger.info(f"Completed {job_type} job successfully")
    except Exception as exc:
        logger.error(f"Failed to execute {job_type} job: {exc}")
        raise


def create_queue() -> BackgroundQueue | RedisQueue:
    """Create the appropriate queue based on environment configuration."""
    # Check if Redis is requested and available
    redis_url = os.getenv("REDIS_URL") or os.getenv("RECRUITPRO_REDIS_URL")
    use_redis = os.getenv("USE_REDIS_QUEUE", "").lower() in ("1", "true", "yes")

    if (redis_url or use_redis) and REDIS_AVAILABLE:
        try:
            queue = RedisQueue(redis_url=redis_url)
            logger.info("✓ Using Redis + RQ for background jobs (production mode)")
            return queue
        except Exception as exc:
            logger.warning(f"Failed to initialize Redis queue: {exc}. Falling back to in-memory queue.")

    # Fall back to in-memory queue
    if not REDIS_AVAILABLE:
        logger.info("Redis/RQ not installed. Using in-memory queue (development mode)")
    else:
        logger.info("Using in-memory queue (development mode)")

    queue = BackgroundQueue()
    queue.start()
    return queue


background_queue = create_queue()
