from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from celery import Task
from celery.utils.log import get_task_logger
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.redis_client import (
    clear_cancellation_flag,
    is_cancelled,
    publish_progress,
)
from app.db.session import async_session_factory
from app.models.job_model import Job, JobStatus
from app.models.result_model import Result
from app.workers.celery_app import celery_app
from app.workers.pipeline_stages import extract_fields, extract_text

logger = get_task_logger(__name__)

def _run(coro: Any) -> Any:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        finally:
            loop.close()


async def _mark_job(
    job_id: uuid.UUID,
    *,
    status: JobStatus,
    stage: str | None = None,
    progress_pct: int | None = None,
    error_message: str | None = None,
) -> None:
    values: dict[str, Any] = {"status": status, "updated_at": datetime.now(timezone.utc)}
    if stage is not None:
        values["current_stage"] = stage
    if progress_pct is not None:
        values["progress_pct"] = progress_pct
    if error_message is not None:
        values["error_message"] = error_message

    async with async_session_factory() as session:
        await session.execute(update(Job).where(Job.id == job_id).values(**values))
        await session.commit()


async def _emit(job_id: uuid.UUID, stage: str, pct: int, metadata: dict | None = None) -> None:
    await publish_progress(
        job_id=job_id,
        event=stage,
        stage=stage,
        progress_pct=pct,
        metadata=metadata,
    )


async def _load_job(job_id: uuid.UUID) -> Job | None:
    async with async_session_factory() as session:
        return await session.scalar(
            select(Job).options(joinedload(Job.document)).where(Job.id == job_id)
        )


async def _is_stale(job_id: uuid.UUID, task_id: str) -> bool:
    async with async_session_factory() as session:
        celery_task_id = (
            await session.execute(select(Job.celery_task_id).where(Job.id == job_id))
        ).scalar_one_or_none()
    return celery_task_id is not None and celery_task_id != task_id


async def _process_document_async(job_id: uuid.UUID, task_id: str) -> dict[str, Any]:
    job = await _load_job(job_id)
    if job is None or job.document is None:
        logger.error("job not found", extra={"job_id": str(job_id)})
        return {"status": "failed", "job_id": str(job_id), "error": "job_not_found"}

    if job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
        return {"status": job.status.value, "job_id": str(job_id)}

    if await _is_stale(job_id, task_id):
        logger.warning("stale task discarded", extra={"job_id": str(job_id), "task_id": task_id})
        return {"status": "stale", "job_id": str(job_id)}

    current_pct = 0
    # Stage: document_received
    await _mark_job(job_id, status=JobStatus.PROCESSING, stage="document_received", progress_pct=current_pct)
    await _emit(job_id, "document_received", current_pct)

    if await is_cancelled(job_id):
        await _mark_job(job_id, status=JobStatus.CANCELLED, stage="job_cancelled", progress_pct=0)
        await _emit(job_id, "job_cancelled", 0, metadata={"reason": "cancelled_before_start"})
        await clear_cancellation_flag(job_id)
        return {"status": "cancelled", "job_id": str(job_id)}

    try:
        # Validate storage path exists before parsing
        from pathlib import Path

        path = Path(job.document.storage_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {job.document.storage_path}")
        if path.stat().st_size == 0:
            raise ValueError("Uploaded file is empty")

        # Stage: parsing_started
        current_pct = 20
        await _mark_job(job_id, status=JobStatus.PROCESSING, stage="parsing_started", progress_pct=current_pct)
        await _emit(job_id, "parsing_started", current_pct)

        parsed = extract_text(job.document.storage_path, job.document.file_type)
        if not parsed.text:
            raise ValueError("No text extracted")

        # Stage: parsing_completed
        current_pct = 40
        await _mark_job(job_id, status=JobStatus.PROCESSING, stage="parsing_completed", progress_pct=current_pct)
        await _emit(job_id, "parsing_completed", current_pct)

        if await is_cancelled(job_id):
            await _mark_job(job_id, status=JobStatus.CANCELLED, stage="job_cancelled", progress_pct=40)
            await _emit(job_id, "job_cancelled", 40, metadata={"reason": "cancelled_after_parsing"})
            await clear_cancellation_flag(job_id)
            return {"status": "cancelled", "job_id": str(job_id)}

        # Stage: extraction_started
        current_pct = 60
        await _mark_job(job_id, status=JobStatus.PROCESSING, stage="extraction_started", progress_pct=current_pct)
        await _emit(job_id, "extraction_started", current_pct)
        fields = extract_fields(parsed, job.document)

        # Stage: extraction_completed (persist)
        async with async_session_factory() as session:
            if await _is_stale(job_id, task_id):
                logger.warning("stale task discarded before persist", extra={"job_id": str(job_id)})
                return {"status": "stale", "job_id": str(job_id)}

            existing = await session.scalar(select(Result).where(Result.job_id == job_id))
            if existing is None:
                session.add(Result(job_id=job_id, raw_output=fields))
            else:
                existing.raw_output = fields

            await session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(
                    current_stage="extraction_completed",
                    progress_pct=80,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

        current_pct = 80
        await _emit(job_id, "extraction_completed", current_pct)

        if await is_cancelled(job_id):
            await _mark_job(job_id, status=JobStatus.CANCELLED, stage="job_cancelled", progress_pct=80)
            await _emit(job_id, "job_cancelled", 80, metadata={"reason": "cancelled_after_extraction"})
            await clear_cancellation_flag(job_id)
            return {"status": "cancelled", "job_id": str(job_id)}

        # Stage: job_completed
        current_pct = 100
        await _mark_job(job_id, status=JobStatus.COMPLETED, stage="job_completed", progress_pct=current_pct)
        await _emit(job_id, "job_completed", current_pct)
        return {"status": "completed", "job_id": str(job_id)}

    except Exception as exc:  # noqa: BLE001
        error_msg = f"{type(exc).__name__}: {exc}"
        await _mark_job(job_id, status=JobStatus.FAILED, stage="job_failed", progress_pct=current_pct, error_message=error_msg)
        await _emit(job_id, "job_failed", current_pct, metadata={"error": error_msg})
        return {"status": "failed", "job_id": str(job_id), "error": error_msg}


@celery_app.task(
    name="app.workers.job_worker.process_document_task",
    bind=True,
    queue="documents",
    autoretry_for=(OSError, ConnectionError),
    retry_kwargs={"max_retries": settings.CELERY_MAX_RETRIES},
    retry_backoff=settings.CELERY_RETRY_BACKOFF_BASE,
    retry_backoff_max=32,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_document_task(self: Task, job_id: str) -> dict[str, Any]:
    logger.info("process_document_task started", extra={"job_id": job_id, "task_id": self.request.id})
    return _run(_process_document_async(uuid.UUID(job_id), self.request.id))
