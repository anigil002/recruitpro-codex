#!/usr/bin/env python3
"""RQ worker for RecruitPro background jobs.

Usage:
    python worker.py                    # Start single worker
    python worker.py --burst             # Process jobs and exit
    python worker.py --name worker-1     # Named worker for monitoring

Environment Variables:
    REDIS_URL or RECRUITPRO_REDIS_URL   # Redis connection string
    LOG_LEVEL                           # Logging level (default: INFO)
"""

import logging
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Start the RQ worker."""
    try:
        import redis
        from rq import Worker
        from rq.job import Job
    except ImportError:
        logger.error("Redis and RQ are required. Install with: pip install redis rq")
        sys.exit(1)

    # Get Redis URL from environment
    redis_url = os.getenv("REDIS_URL") or os.getenv("RECRUITPRO_REDIS_URL", "redis://localhost:6379/0")

    try:
        # Connect to Redis
        redis_conn = redis.from_url(
            redis_url,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        redis_conn.ping()
        logger.info(f"✓ Connected to Redis at {redis_url}")
    except Exception as exc:
        logger.error(f"Failed to connect to Redis: {exc}")
        logger.error(f"Make sure Redis is running and REDIS_URL is set correctly")
        sys.exit(1)

    # Import the app to register all job handlers
    try:
        logger.info("Loading RecruitPro application and registering job handlers...")
        from app.services.queue import background_queue, _HANDLER_REGISTRY

        # Import ai service to ensure handlers are registered
        from app.services import ai as ai_service
        _ = ai_service  # Ensure module is loaded

        logger.info(f"✓ Registered {len(_HANDLER_REGISTRY)} job handlers:")
        for job_type in sorted(_HANDLER_REGISTRY.keys()):
            logger.info(f"  - {job_type}")

    except Exception as exc:
        logger.error(f"Failed to load application: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="RecruitPro RQ Worker")
    parser.add_argument("--burst", action="store_true", help="Run in burst mode (process jobs and exit)")
    parser.add_argument("--name", type=str, default=None, help="Worker name for monitoring")
    parser.add_argument("--queue", type=str, default="recruitpro", help="Queue name (default: recruitpro)")
    args = parser.parse_args()

    # Create worker
    worker = Worker(
        [args.queue],
        connection=redis_conn,
        name=args.name,
    )

    logger.info(f"✓ Starting RQ worker{' (burst mode)' if args.burst else ''}...")
    logger.info(f"  Queue: {args.queue}")
    logger.info(f"  Worker name: {worker.name}")
    logger.info("")
    logger.info("Worker is ready to process jobs. Press Ctrl+C to stop.")
    logger.info("")

    try:
        worker.work(burst=args.burst, with_scheduler=False)
    except KeyboardInterrupt:
        logger.info("\nShutting down worker...")
    except Exception as exc:
        logger.error(f"Worker error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
