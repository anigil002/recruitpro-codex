"""Tests for the realtime event broker used by server-sent events."""

import asyncio

import pytest

from app.services.realtime import EventBroker


def test_subscribe_cancellation_closes_stream() -> None:
    """Cancelling a subscriber should terminate the generator cleanly."""

    async def runner() -> None:
        broker = EventBroker()
        stream = broker.subscribe()

        task = asyncio.create_task(stream.__anext__())

        await asyncio.sleep(0)
        task.cancel()

        with pytest.raises(StopAsyncIteration):
            await task

        with pytest.raises(StopAsyncIteration):
            await stream.__anext__()

        assert broker._subscribers == []

    asyncio.run(runner())
