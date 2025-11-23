"""
Background Queue System using Redis + RQ

This module provides a production-ready background task queue system for
processing long-running tasks asynchronously (AI processing, file analysis, etc.)

Features:
- Redis-based job queue with RQ
- Automatic retry with exponential backoff
- Job status persistence
- Failed job tracking
- Result storage

Usage:
    from app.queue import enqueue_job, get_job_status

    # Enqueue a job
    job = enqueue_job('app.tasks.process_cv', cv_data, timeout='10m')

    # Check job status
    status = get_job_status(job.id)
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import redis
from rq import Queue, Retry, Worker
from rq.job import Job

from .config import get_settings

settings = get_settings()

# Redis connection
redis_conn = redis.from_url(settings.redis_url)

# Define queues with different priorities
default_queue = Queue("default", connection=redis_conn)
high_priority_queue = Queue("high", connection=redis_conn)
low_priority_queue = Queue("low", connection=redis_conn)


def enqueue_job(
    func: str,
    *args: Any,
    queue_name: str = "default",
    timeout: str = "10m",
    retry: Optional[Retry] = None,
    result_ttl: int = 3600,
    **kwargs: Any,
) -> Job:
    """
    Enqueue a background job for processing.

    Args:
        func: Function path as string (e.g., 'app.tasks.process_cv')
        *args: Positional arguments for the function
        queue_name: Queue to use ('default', 'high', 'low')
        timeout: Job timeout (e.g., '5m', '1h', '30s')
        retry: Retry configuration. If None, uses default (3 retries with exponential backoff)
        result_ttl: How long to keep job results (seconds). Default: 1 hour
        **kwargs: Keyword arguments for the function

    Returns:
        Job: RQ Job object with id, status, result, etc.

    Example:
        job = enqueue_job(
            'app.tasks.screen_candidate',
            candidate_id='c123',
            position_id='p456',
            timeout='15m',
        )
        print(f"Job queued: {job.id}")
    """
    # Select queue
    queue_map = {
        "default": default_queue,
        "high": high_priority_queue,
        "low": low_priority_queue,
    }
    queue = queue_map.get(queue_name, default_queue)

    # Default retry: 3 attempts with exponential backoff (1s, 2s, 4s)
    if retry is None:
        retry = Retry(max=3, interval=[1, 2, 4])

    # Enqueue the job
    job = queue.enqueue(
        func,
        *args,
        retry=retry,
        job_timeout=timeout,
        result_ttl=result_ttl,
        failure_ttl=86400,  # Keep failed jobs for 24 hours
        **kwargs,
    )

    return job


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status of a background job.

    Args:
        job_id: Job ID returned from enqueue_job()

    Returns:
        Dict with job status information:
        {
            'id': 'job_id',
            'status': 'queued'|'started'|'finished'|'failed'|'canceled',
            'result': result if finished,
            'error': error message if failed,
            'created_at': timestamp,
            'started_at': timestamp,
            'ended_at': timestamp,
            'position': queue position (if queued),
        }
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)

        status_data = {
            "id": job.id,
            "status": job.get_status(),
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        }

        # Add result if job is finished
        if job.is_finished:
            status_data["result"] = job.result

        # Add error if job failed
        if job.is_failed:
            status_data["error"] = str(job.exc_info) if job.exc_info else "Unknown error"

        # Add queue position if job is queued
        if job.is_queued:
            position = job.get_position()
            status_data["position"] = position

        return status_data

    except Exception as e:
        return {
            "id": job_id,
            "status": "not_found",
            "error": str(e),
        }


def cancel_job(job_id: str) -> bool:
    """
    Cancel a queued or running job.

    Args:
        job_id: Job ID to cancel

    Returns:
        bool: True if canceled successfully, False otherwise
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        job.cancel()
        return True
    except Exception:
        return False


def get_queue_stats() -> Dict[str, Any]:
    """
    Get statistics for all queues.

    Returns:
        Dict with queue statistics:
        {
            'default': {'queued': 10, 'started': 2, 'finished': 100, 'failed': 5},
            'high': {...},
            'low': {...},
        }
    """
    queues = {
        "default": default_queue,
        "high": high_priority_queue,
        "low": low_priority_queue,
    }

    stats = {}
    for name, queue in queues.items():
        stats[name] = {
            "queued": len(queue),
            "started": queue.started_job_registry.count,
            "finished": queue.finished_job_registry.count,
            "failed": queue.failed_job_registry.count,
        }

    return stats


def cleanup_old_jobs(hours: int = 24) -> int:
    """
    Clean up finished and failed jobs older than specified hours.

    Args:
        hours: Age threshold in hours

    Returns:
        int: Number of jobs cleaned up
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    cleaned = 0

    for queue in [default_queue, high_priority_queue, low_priority_queue]:
        # Clean finished jobs
        for job_id in queue.finished_job_registry.get_job_ids():
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                if job.ended_at and job.ended_at < cutoff:
                    job.delete()
                    cleaned += 1
            except Exception:
                pass

        # Clean failed jobs
        for job_id in queue.failed_job_registry.get_job_ids():
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                if job.ended_at and job.ended_at < cutoff:
                    job.delete()
                    cleaned += 1
            except Exception:
                pass

    return cleaned
