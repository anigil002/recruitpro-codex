"""Simple publish/subscribe broker used for Server-Sent Events."""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Dict, List, Optional, Tuple

import anyio


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: List[Tuple[asyncio.Queue, Optional[str]]] = []
        self._lock = threading.Lock()

    async def subscribe(self, *, user_id: Optional[str] = None):
        queue: asyncio.Queue = asyncio.Queue()
        with self._lock:
            self._subscribers.append((queue, user_id))
        try:
            while True:
                try:
                    event = await queue.get()
                except asyncio.CancelledError:
                    # When the server is shutting down (for example because the
                    # developer pressed CTRL+C) ``queue.get`` is cancelled.  If
                    # we allow the ``CancelledError`` to propagate it bubbles up
                    # through FastAPI's streaming response machinery and
                    # eventually surfaces as an error during shutdown on Python
                    # 3.13/Windows.  By breaking out of the generator loop we
                    # terminate the stream cleanly while still allowing the
                    # cancellation to unwind the caller's task.
                    break
                yield event
        finally:
            with self._lock:
                self._subscribers = [item for item in self._subscribers if item[0] is not queue]

    async def publish(self, event: Dict[str, Any]) -> None:
        dead: List[int] = []
        with self._lock:
            subscribers = list(self._subscribers)
        for index, (queue, user_filter) in enumerate(subscribers):
            if user_filter and event.get("user_id") not in (None, user_filter):
                continue
            try:
                await queue.put(event)
            except RuntimeError:
                dead.append(index)
        if dead:
            with self._lock:
                for index in sorted(dead, reverse=True):
                    try:
                        del self._subscribers[index]
                    except IndexError:
                        continue

    def publish_sync(self, event: Dict[str, Any]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                anyio.from_thread.run(self.publish, event)
            except Exception:
                asyncio.run(self.publish(event))
        else:
            loop.create_task(self.publish(event))


events = EventBroker()
