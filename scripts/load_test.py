"""Lightweight load testing harness for RecruitPro endpoints.

This script uses httpx's ASGI transport to exercise the FastAPI app without
requiring an external server. It initializes the database, sends concurrent
requests, and reports latency metrics. Use command-line options to adjust
request counts or target path.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
from time import perf_counter
from typing import List

import httpx

# Ensure load testing does not overwrite a production database file by default.
os.environ.setdefault("RECRUITPRO_DATABASE_URL", "sqlite:///./data/load_test.db")

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402


async def _issue_request(client: httpx.AsyncClient, url: str, semaphore: asyncio.Semaphore) -> float:
    """Send a single request and return the latency in milliseconds."""

    async with semaphore:
        start = perf_counter()
        response = await client.get(url)
        response.raise_for_status()
        return (perf_counter() - start) * 1000


async def run_load_test(path: str, requests: int, concurrency: int) -> dict:
    """Execute a burst of requests against the ASGI app."""

    init_db()
    semaphore = asyncio.Semaphore(concurrency)
    latencies: List[float] = []

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        tasks = [_issue_request(client, path, semaphore) for _ in range(requests)]
        for latency in await asyncio.gather(*tasks):
            latencies.append(latency)

    return {
        "requests": requests,
        "concurrency": concurrency,
        "min_ms": round(min(latencies), 3),
        "max_ms": round(max(latencies), 3),
        "avg_ms": round(sum(latencies) / len(latencies), 3),
        "p95_ms": round(statistics.quantiles(latencies, n=100)[94], 3),
        "p99_ms": round(statistics.quantiles(latencies, n=100)[98], 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="RecruitPro load testing helper")
    parser.add_argument("--path", default="/api/health", help="Endpoint path to exercise")
    parser.add_argument("--requests", type=int, default=100, help="Total number of requests to send")
    parser.add_argument("--concurrency", type=int, default=20, help="Maximum concurrent requests")
    args = parser.parse_args()

    summary = asyncio.run(run_load_test(args.path, args.requests, args.concurrency))
    print("Load test summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
