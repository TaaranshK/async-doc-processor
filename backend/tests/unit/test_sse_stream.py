from __future__ import annotations

import json
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from app.controllers import job_controller


class FakePubSub:
    def __init__(self, message):
        self._message = message
        self._sent = False

    async def subscribe(self, channel):  # noqa: ARG002
        return None

    async def get_message(self, **kwargs):  # noqa: ARG002
        if self._sent:
            return None
        self._sent = True
        return self._message

    async def unsubscribe(self, channel):  # noqa: ARG002
        return None

    async def aclose(self):
        return None


class FakeRedis:
    def __init__(self, message):
        self._message = message

    def pubsub(self):
        return FakePubSub(self._message)


@pytest.mark.asyncio
async def test_sse_generator_emits_event(monkeypatch):
    job_id = uuid4()
    payload = {
        "event": "job_completed",
        "job_id": str(job_id),
        "stage": "job_completed",
        "progress_pct": 100,
        "timestamp": "2026-04-13T10:00:00Z",
        "metadata": {},
    }
    message = {"data": json.dumps(payload)}

    @asynccontextmanager
    async def fake_get_redis():
        yield FakeRedis(message)

    monkeypatch.setattr(job_controller, "get_redis", fake_get_redis)

    generator = job_controller._sse_event_generator(job_id)
    event = await anext(generator)

    assert "event: job_completed" in event
    assert "job_completed" in event
