from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------

_pool: aioredis.ConnectionPool | None = None


def get_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True,
        )
    return _pool


@asynccontextmanager
async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client = aioredis.Redis(connection_pool=get_pool())
    try:
        yield client
    finally:
        await client.aclose()


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        logger.info("Redis connection pool closed")


# ---------------------------------------------------------------------------
# Pub/Sub channels
# ---------------------------------------------------------------------------


def pubsub_channel(job_id: UUID | str) -> str:
    return f"job_progress:{job_id}"


def cancellation_key(job_id: UUID | str) -> str:
    return f"cancel:{job_id}"


# ---------------------------------------------------------------------------
# Progress publishing
# ---------------------------------------------------------------------------


def build_progress_payload(
    *,
    job_id: UUID | str,
    event: str,
    stage: str,
    progress_pct: int,
    metadata: dict | None = None,
) -> dict:
    return {
        "event": event,
        "job_id": str(job_id),
        "stage": stage,
        "progress_pct": max(0, min(100, progress_pct)),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }


async def publish_progress(
    *,
    job_id: UUID | str,
    event: str,
    stage: str,
    progress_pct: int,
    metadata: dict | None = None,
) -> None:
    payload = build_progress_payload(
        job_id=job_id,
        event=event,
        stage=stage,
        progress_pct=progress_pct,
        metadata=metadata,
    )
    message = json.dumps(payload)
    channel = pubsub_channel(job_id)

    async with get_redis() as redis:
        subscribers = await redis.publish(channel, message)

    logger.debug(
        "progress event published",
        extra={
            "job_id": str(job_id),
            "event": event,
            "progress_pct": progress_pct,
            "subscribers": subscribers,
        },
    )


# ---------------------------------------------------------------------------
# Progress subscription (optional utility)
# ---------------------------------------------------------------------------


async def subscribe_progress(
    job_id: UUID | str,
    *,
    timeout: float = 300.0,
    keepalive: float = 15.0,
) -> AsyncGenerator[dict, None]:
    channel = pubsub_channel(job_id)
    client = aioredis.Redis(connection_pool=get_pool())
    pubsub = client.pubsub()

    try:
        await pubsub.subscribe(channel)
        terminal_events = {"job_completed", "job_failed", "job_cancelled"}

        while True:
            try:
                raw = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=keepalive),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("SSE subscription timed out", extra={"job_id": str(job_id)})
                break

            if raw is None:
                yield {"_keepalive": True}
                continue

            try:
                event = json.loads(raw["data"])
            except (json.JSONDecodeError, KeyError) as exc:
                logger.error("malformed pub/sub message", extra={"error": str(exc)})
                continue

            yield event

            if event.get("event") in terminal_events:
                break
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await client.aclose()


# ---------------------------------------------------------------------------
# Cancellation flags
# ---------------------------------------------------------------------------


async def set_cancellation_flag(job_id: UUID | str, ttl: int = 3600) -> None:
    async with get_redis() as redis:
        await redis.set(cancellation_key(job_id), "1", ex=ttl)


async def is_cancelled(job_id: UUID | str) -> bool:
    async with get_redis() as redis:
        return await redis.exists(cancellation_key(job_id)) == 1


async def clear_cancellation_flag(job_id: UUID | str) -> None:
    async with get_redis() as redis:
        await redis.delete(cancellation_key(job_id))
