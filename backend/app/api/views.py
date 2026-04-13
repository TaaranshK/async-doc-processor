"""
This file handles all the job-related endpoints.

It provides these main actions:
- Get a list of all jobs
- Get details about a specific job
- Watch live progress of a job
- Get job results
- Update results
- Restart a failed job
- Cancel a job
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select, update

from app.api.dependencies import (
    ActiveJobDep,
    CurrentUser,
    DbSession,
    FailedJobDep,
    JobDep,
    JobFilterDep,
    JobResultDep,
    PaginationDep,
    RedisClient,
)
from app.models.job import Job, JobStatus
from app.models.result import Result
from app.schemas.job import JobDetailResponse, JobListResponse, JobSummary
from app.schemas.result import ResultResponse, ReviewedOutputUpdate
from app.services.job_service import JobService
from app.workers.tasks import process_document_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Get all jobs with filtering, searching, and sorting
@router.get("", response_model=JobListResponse)
async def list_jobs(
    db: DbSession,
    current_user: CurrentUser,
    filters: JobFilterDep,
    pagination: PaginationDep,
) -> JobListResponse:
    # This function returns a list of all jobs for the logged-in user
    # It supports searching by filename, filtering by status, and sorting
    stmt = (
        select(Job)
        .join(Job.document)
        .where(Job.uploaded_by == current_user.id)
    )

    # If user wants to search, add that filter
    if filters.search:
        pattern = f"%{filters.search}%"
        stmt = stmt.where(Job.document.has(filename=None) | Job.document.property.mapper.class_.filename.ilike(pattern))  # type: ignore[attr-defined]

    # If user wants to filter by job status, add that filter
    if filters.status:
        stmt = stmt.where(Job.status.in_(filters.status))

    # Count total number of jobs for showing in results
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    # Pick what column to sort by (either created date or status)
    sort_col = Job.created_at if filters.sort_by == "created_at" else Job.status
    stmt = stmt.order_by(
        sort_col.desc() if filters.sort_order == "desc" else sort_col.asc()
    )

    stmt = stmt.offset(pagination.offset).limit(pagination.limit)
    rows = (await db.execute(stmt)).scalars().all()

    return JobListResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        items=[JobSummary.model_validate(job) for job in rows],
    )


# Get details about a specific job
@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(job: JobDep) -> JobDetailResponse:
    # This returns all the details about one job, like its status and progress
    return JobDetailResponse.model_validate(job)


# Stream live progress updates for a job
# How often we check if client is still connected (in seconds)
_SSE_KEEPALIVE_INTERVAL = 15
# Job states that mean the job is done processing
_SSE_TERMINAL_STATES = {JobStatus.completed, JobStatus.failed, JobStatus.cancelled}


async def _sse_event_generator(
    job_id: UUID,
    redis: RedisClient,
) -> AsyncGenerator[str, None]:
    # This watches for progress updates from Redis and sends them to the user
    # It keeps sending updates until the job is done or the user closes the connection
    channel_name = f"job_progress:{job_id}"
    pubsub = redis.pubsub()

    try:
        await pubsub.subscribe(channel_name)
        logger.debug("SSE: subscribed to %s", channel_name)

        while True:
            # Check if there's a new message, but don't wait forever
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=_SSE_KEEPALIVE_INTERVAL
            )

            # If no message, send a keepalive signal to keep connection alive
            if message is None:
                # Send SSE comment as keepalive to prevent proxy timeouts
                yield ": keepalive\n\n"
                continue

            raw: str = message.get("data", "")
            if not raw:
                continue

            try:
                payload: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("SSE: invalid JSON on channel %s: %r", channel_name, raw)
                continue

            event_type: str = payload.get("event", "progress")
            yield f"event: {event_type}\ndata: {raw}\n\n"

            # Auto-close stream when the job has finished
            progress_pct: int = payload.get("progress_pct", 0)
            stage: str = payload.get("stage", "")
            if progress_pct >= 100 or stage == "job_completed":
                logger.debug("SSE: terminal event received for job %s, closing stream", job_id)
                return

    except asyncio.CancelledError:
        # Client disconnected
        logger.debug("SSE: client disconnected from job %s", job_id)
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.aclose()
        logger.debug("SSE: released subscription for %s", channel_name)


@router.get("/{job_id}/progress")
async def stream_job_progress(
    job: JobDep,
    redis: RedisClient,
) -> StreamingResponse:
    """
    Stream live progress events for a job via Server-Sent Events.

    - If the job is already in a terminal state, returns a single
      synthetic event so the client can close immediately.
    - Otherwise, subscribes to Redis Pub/Sub and forwards events.
    - On client disconnect, subscription is released (no resource leak).
    """
    if job.status in _SSE_TERMINAL_STATES:
        # Emit one final event for already-finished jobs and close
        async def _terminal_stream() -> AsyncGenerator[str, None]:
            synthetic = json.dumps(
                {
                    "event": "job_completed" if job.status == JobStatus.completed else str(job.status),
                    "job_id": str(job.id),
                    "progress_pct": 100 if job.status == JobStatus.completed else job.progress_pct,
                    "stage": str(job.status),
                    "timestamp": job.updated_at.isoformat(),
                    "metadata": {},
                }
            )
            yield f"event: {job.status}\ndata: {synthetic}\n\n"

        return StreamingResponse(
            _terminal_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return StreamingResponse(
        _sse_event_generator(job.id, redis),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}/result  — fetch extracted + reviewed output
# ---------------------------------------------------------------------------


@router.get("/{job_id}/result", response_model=ResultResponse)
async def get_job_result(result: JobResultDep) -> ResultResponse:
    """Return the raw and reviewed output for a completed job."""
    return ResultResponse.model_validate(result)


# ---------------------------------------------------------------------------
# PUT /jobs/{job_id}/result  — update reviewed fields
# ---------------------------------------------------------------------------


@router.put("/{job_id}/result", response_model=ResultResponse)
async def update_reviewed_output(
    job: JobDep,
    result: JobResultDep,
    body: ReviewedOutputUpdate,
    db: DbSession,
) -> ResultResponse:
    """
    Persist user edits to the reviewed_output JSONB column.

    - Fields are read-only once ``is_finalized`` is True.
    - Partial updates are supported: only keys present in the request body
      are merged into the existing reviewed_output.
    """
    if result.is_finalized:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot edit a finalized result",
        )

    # Merge incoming fields onto existing reviewed_output (partial update)
    current: dict[str, Any] = result.reviewed_output or {}
    merged = {**current, **body.fields}

    await db.execute(
        update(Result)
        .where(Result.id == result.id)
        .values(reviewed_output=merged)
    )
    await db.commit()
    await db.refresh(result)

    return ResultResponse.model_validate(result)


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/finalize
# ---------------------------------------------------------------------------


@router.post("/{job_id}/finalize", response_model=ResultResponse)
async def finalize_result(
    job: JobDep,
    result: JobResultDep,
    db: DbSession,
) -> ResultResponse:
    """
    Mark a result as finalized.

    - Idempotent: calling finalize on an already-finalized result is a no-op.
    - Once finalized, reviewed_output is immutable and export becomes available.
    """
    if result.is_finalized:
        # Idempotent — return current state without error
        return ResultResponse.model_validate(result)

    from datetime import datetime, timezone

    await db.execute(
        update(Result)
        .where(Result.id == result.id)
        .values(
            is_finalized=True,
            finalized_at=datetime.now(tz=timezone.utc),
        )
    )
    await db.commit()
    await db.refresh(result)

    logger.info("Result finalized: job_id=%s result_id=%s", job.id, result.id)
    return ResultResponse.model_validate(result)


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/retry
# ---------------------------------------------------------------------------


@router.post("/{job_id}/retry", response_model=JobDetailResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_job(
    job: FailedJobDep,
    db: DbSession,
) -> JobDetailResponse:
    """
    Re-enqueue a failed job.

    Per PRD retry strategy:
    - A new Celery task is dispatched with a fresh ``celery_task_id``
    - ``retry_count`` is incremented
    - ``progress_pct`` resets to 0 and ``status`` returns to ``queued``
    - Idempotency is enforced in the worker by checking ``celery_task_id``
      before writing results; the old task ID is no longer referenced
    """
    celery_result = process_document_task.apply_async(
        kwargs={"job_id": str(job.id)},
    )

    await db.execute(
        update(Job)
        .where(Job.id == job.id)
        .values(
            status=JobStatus.queued,
            celery_task_id=celery_result.id,
            progress_pct=0,
            current_stage=None,
            error_message=None,
            retry_count=Job.retry_count + 1,
        )
    )
    await db.commit()
    await db.refresh(job)

    logger.info(
        "Job retried: job_id=%s new_celery_task_id=%s retry_count=%d",
        job.id,
        celery_result.id,
        job.retry_count,
    )
    return JobDetailResponse.model_validate(job)


# ---------------------------------------------------------------------------
# POST /jobs/{job_id}/cancel
# ---------------------------------------------------------------------------

_CANCEL_FLAG_TTL = 3600  # seconds; auto-expires in case worker never checks


@router.post("/{job_id}/cancel", response_model=JobDetailResponse)
async def cancel_job(
    job: ActiveJobDep,
    db: DbSession,
    redis: RedisClient,
) -> JobDetailResponse:
    """
    Cancel a queued or processing job.

    Steps (per PRD §7.3):
    1. Set a cancellation flag in Redis so in-progress workers exit cleanly
       at the next stage boundary.
    2. Call ``celery.control.revoke`` to prevent the task from starting if
       still queued, and to send SIGTERM if it is already executing.
    3. Update the job's DB status to ``cancelled``.

    Workers check ``cancel:{job_id}`` in Redis at the start of each stage
    and exit without writing partial results when the flag is present.
    """
    from celery.app.control import Control  # type: ignore[import-untyped]

    from app.core.celery_app import celery_app

    # 1. Set cancellation flag for in-progress workers
    cancel_key = f"cancel:{job.id}"
    await redis.setex(cancel_key, _CANCEL_FLAG_TTL, "1")

    # 2. Revoke the Celery task (terminate=True sends SIGTERM to the worker)
    if job.celery_task_id:
        control: Control = celery_app.control
        control.revoke(job.celery_task_id, terminate=True, signal="SIGTERM")
        logger.info(
            "Celery task revoked: job_id=%s celery_task_id=%s",
            job.id,
            job.celery_task_id,
        )

    # 3. Persist cancelled status
    await db.execute(
        update(Job)
        .where(Job.id == job.id)
        .values(status=JobStatus.cancelled)
    )
    await db.commit()
    await db.refresh(job)

    logger.info("Job cancelled: job_id=%s", job.id)
    return JobDetailResponse.model_validate(job)