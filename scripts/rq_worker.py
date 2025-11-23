#!/usr/bin/env python3
"""
RQ Worker Script

This script starts an RQ worker to process background jobs from Redis queues.
Multiple workers can be run in parallel for increased throughput.

Usage:
    # Start a worker for all queues (default, high, low)
    python scripts/rq_worker.py

    # Start a worker for specific queues
    python scripts/rq_worker.py --queues high default

    # Start worker with custom burst mode (process jobs and exit)
    python scripts/rq_worker.py --burst

Configuration:
    - Redis URL: Set RECRUITPRO_REDIS_URL in .env
    - Worker name: Auto-generated or set with --name

Production Deployment:
    Use a process manager like supervisord or systemd to run multiple workers:

    # systemd service file: /etc/systemd/system/recruitpro-worker@.service
    [Unit]
    Description=RecruitPro RQ Worker %i
    After=network.target redis.service

    [Service]
    Type=simple
    User=recruitpro
    WorkingDirectory=/opt/recruitpro
    Environment="PATH=/opt/recruitpro/venv/bin"
    ExecStart=/opt/recruitpro/venv/bin/python scripts/rq_worker.py
    Restart=always

    [Install]
    WantedBy=multi-user.target

    # Start multiple workers
    sudo systemctl start recruitpro-worker@1
    sudo systemctl start recruitpro-worker@2
    sudo systemctl start recruitpro-worker@3
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rq import Worker

from app.config import get_settings
from app.queue import default_queue, high_priority_queue, low_priority_queue, redis_conn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='RQ Worker for RecruitPro')
    parser.add_argument(
        '--queues',
        nargs='+',
        default=['high', 'default', 'low'],
        choices=['high', 'default', 'low'],
        help='Queues to process (default: high, default, low)'
    )
    parser.add_argument(
        '--name',
        help='Worker name (default: auto-generated)'
    )
    parser.add_argument(
        '--burst',
        action='store_true',
        help='Run in burst mode (process jobs and exit)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get settings
    settings = get_settings()

    # Map queue names to queue objects
    queue_map = {
        'high': high_priority_queue,
        'default': default_queue,
        'low': low_priority_queue,
    }

    # Get queues in order specified
    queues = [queue_map[name] for name in args.queues]

    logger.info(f"Starting RQ worker for queues: {args.queues}")
    logger.info(f"Redis URL: {settings.redis_url}")

    # Create worker
    worker = Worker(
        queues,
        connection=redis_conn,
        name=args.name,
    )

    # Start worker
    try:
        worker.work(burst=args.burst)
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
