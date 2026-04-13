rom __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import UUID

import redis.asyncio as aioredis

from app.core.config import settings
# ------
# Connection pool setup
# ------
# Here we create and manage a shared connection to Redis

_pool: aioredis.ConnectionPool | None = None


def get_pool() -> aioredis.ConnectionPool:
    # Get or create the Redis connection pool
    # The pool lets multiple requests share Redis connections efficiently
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
    # This gives you a temporary Redis client to use
    # Automatically closes the connection when done
    client = aioredis.Redis(connection_pool=get_pool())
    try:
        yield client
    finally:
        await client.aclose()


async def close_pool() -> None:
    # Close the Redis connection pool when the app shuts down
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        logger.info("Redis connection pool closed")


# -----
# Pub/Sub channel naming
# -----
# These functions create the names for Redis channels

def pubsub_channel(job_id: UUID | str) -> str:
    # Get the channel name where we send progress updates for a job
    return f"job_progress:{job_id}"


def cancellation_key(job_id: UUID | str) -> str:
    # Get the key where we store the cancel flag for a job
    return f"job_cancel:{job_id}"


# -----------
# Publishing (called from background workers)
# -----------

async def publish_progress(
    job_id: UUID | str,
    event: str,
    stage: str,
    progress_pct: int,
    metadata: dict | None = None,
) -> None:
    # Send a progress update about a job to anyone listening
    # This tells the UI what percentage is done and which stage we're on
    from datetime import datetime, timezone

    payload = {
        "event":        event,
        "job_id":       str(job_id),
        "stage":        stage,
        "progress_pct": max(0, min(100, progress_pct)),
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "metadata":     metadata or {},
    }

    channel = pubsub_channel(job_id)
    message = json.dumps(payload)

    async with get_redis() as r:
        subscribers = await r.publish(channel, message)

    logger.debug(
        "progress event published",
        extra={
            "job_id":       str(job_id),
            "event":        event,
            "progress_pct": progress_pct,
            "subscribers":  subscribers,
        },
    )


# -----------
# Subscribing to progress updates (called from the frontend)
# -----------

async def subscribe_progress(
    job_id: UUID | str,
    timeout: float = 300.0,
) -> AsyncGenerator[dict, None]:
    # Watch for progress updates on a specific job
    # Stops when the job is done or the timeout is reached
    channel = pubsub_channel(job_id)
    client = aioredis.Redis(connection_pool=get_pool())
    pubsub = client.pubsub()

    try:
        await pubsub.subscribe(channel)
        logger.debug("subscribed to progress channel", extra={"channel": channel})

        terminal_events = {"job_completed", "job_failed", "job_cancelled"}

        while True:
            try:
                raw = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "SSE subscription timed out",
                    extra={"job_id": str(job_id)},
                )
                break

            if raw is None:
                # No message yet — yield control and try again
                await asyncio.sleep(0.05)
                continue

            try:
                event = json.loads(raw["data"])
            except (json.JSONDecodeError, KeyError) as exc:
                logger.error(
                    "malformed pub/sub message",
                    extra={"raw": raw, "error": str(exc)},
                )
                continue

            yield event

            if event.get("event") in terminal_events:
                break

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await client.aclose()
        logger.debug("unsubscribed from progress channel", extra={"channel": channel})


# ---------------------------------------------------------------------------
# Cancellation flag helpers (called from worker and cancel endpoint)
# -----------
# Cancellation (telling the worker to stop a job)
# -----------

async def set_cancellation_flag(job_id: UUID | str, ttl: int = 3600) -> None:
    # Tell the worker to stop processing this job
    async with get_redis() as r:
        await r.set(cancellation_key(job_id), "1", ex=ttl)


async def is_cancelled(job_id: UUID | str) -> bool:
    # Check if someone asked to stop this job
    async with get_redis() as r:
        return await r.exists(cancellation_key(job_id)) == 1


async def clear_cancellation_flag(job_id: UUID | str) -> None:
    # Remove the stop signal after the job has been stopped
    async with get_redis() as r:
        await r.delete(cancellation_key(job_id))