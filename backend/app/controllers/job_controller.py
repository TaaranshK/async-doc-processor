from __future__ import annotations

import asyncio
import json
from typing import Annotated, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis, pubsub_channel
from app.db.session import get_db
from app.models.job_model import JobStatus
from app.schemas.job_schema import JobDetailResponse, JobFilterParams, JobListResponse
from app.schemas.result_schema import ResultResponse, ResultUpdateRequest
from app.services.job_service import JobService
from app.services.result_service import ResultService

router = APIRouter(prefix="/jobs", tags=["jobs"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

_SSE_KEEPALIVE_INTERVAL = 15
_TERMINAL_EVENTS = {"job_completed", "job_failed", "job_cancelled"}
_TERMINAL_STATES = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}


@router.get("", response_model=JobListResponse)
async def list_jobs(
    params: Annotated[JobFilterParams, Depends()],
    db: DbSession,
) -> JobListResponse:
    return await JobService(db).list_jobs(params)


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(job_id: UUID, db: DbSession) -> JobDetailResponse:
    return await JobService(db).get_job_detail(job_id)


async def _sse_event_generator(job_id: UUID) -> AsyncGenerator[str, None]:
    channel = pubsub_channel(job_id)
    async with get_redis() as redis:
        pubsub = redis.pubsub()
        try:
            await pubsub.subscribe(channel)
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=_SSE_KEEPALIVE_INTERVAL,
                )
                if message is None:
                    yield ": keepalive\n\n"
                    continue

                raw = message.get("data")
                if not raw:
                    continue

                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                event_type = payload.get("event", "progress")
                yield f"event: {event_type}\ndata: {raw}\n\n"

                if event_type in _TERMINAL_EVENTS:
                    return
        except asyncio.CancelledError:
            return
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


@router.get("/{job_id}/progress")
async def stream_job_progress(job_id: UUID, db: DbSession) -> StreamingResponse:
    service = JobService(db)
    job = await service.get_job(job_id)

    if job.status in _TERMINAL_STATES:
        async def _terminal_stream() -> AsyncGenerator[str, None]:
            payload = {
                "event": "job_completed" if job.status == JobStatus.COMPLETED else f"job_{job.status.value}",
                "job_id": str(job.id),
                "stage": job.current_stage or job.status.value,
                "progress_pct": job.progress_pct,
                "timestamp": job.updated_at.isoformat(),
                "metadata": {},
            }
            yield f"event: {payload['event']}\ndata: {json.dumps(payload)}\n\n"

        return StreamingResponse(
            _terminal_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return StreamingResponse(
        _sse_event_generator(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{job_id}/result", response_model=ResultResponse)
async def get_job_result(job_id: UUID, db: DbSession) -> ResultResponse:
    return ResultResponse.model_validate(await ResultService(db).get_result(job_id))


@router.put("/{job_id}/result", response_model=ResultResponse)
async def update_job_result(
    job_id: UUID,
    payload: ResultUpdateRequest,
    db: DbSession,
) -> ResultResponse:
    return await ResultService(db).update_result(job_id, payload)


@router.post("/{job_id}/finalize", response_model=ResultResponse)
async def finalize_job_result(job_id: UUID, db: DbSession) -> ResultResponse:
    return await ResultService(db).finalize_result(job_id)


@router.post("/{job_id}/retry", response_model=JobDetailResponse)
async def retry_job(job_id: UUID, db: DbSession) -> JobDetailResponse:
    return await JobService(db).retry_job(job_id)


@router.post("/{job_id}/cancel", response_model=JobDetailResponse)
async def cancel_job(job_id: UUID, db: DbSession) -> JobDetailResponse:
    return await JobService(db).cancel_job(job_id)
