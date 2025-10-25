"""In-process background queue used to emulate the worker architecture."""

from __future__ import annotations

import logging
from datetime import datetime
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Any, Callable, Dict, Optional


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


background_queue = BackgroundQueue()
background_queue.start()
