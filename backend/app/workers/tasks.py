"""
Worker tasks that handle processing documents in the background.

Main tasks:
- process_document: Handles the full document processing workflow
- cancel_document: Stops a job that's currently running or waiting
- reap_orphaned_jobs: Cleans up jobs that got stuck

These tasks run in the background and do all the heavy processing work.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from sqlalchemy import select, update

from app.core.redis_client import (
    clear_cancellation_flag,
    is_cancelled,
    publish_progress,
)
from app.db.session import async_session_factory
from app.models.job import Job, JobStatus
from app.schemas.progress import ProgressEvent
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)

# -----------
# Helpers
# -----------


def _run(coro: Any) -> Any:
    # This helper runs async code inside a Celery task
    # Celery workers are synchronous, but we need to run async functions
    # So we create a new event loop, run the async code, then close it
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        # Clean up leftover tasks and close the event loop
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
        finally:
            loop.close()


async def _mark_job(
    job_id: uuid.UUID,
    status: JobStatus,
    *,
    error_message: str | None = None,
    current_stage: str | None = None,
    progress_pct: int | None = None,
) -> None:
    # This updates a job's status in the database
    # It can set the status, error message, current stage, and progress percentage
    values: dict[str, Any] = {
        "status": status,
        "updated_at": datetime.now(tz=timezone.utc),
    }
    if error_message is not None:
        values["error_message"] = error_message
    if current_stage is not None:
        values["current_stage"] = current_stage
    if progress_pct is not None:
        values["progress_pct"] = progress_pct

    async with async_session_factory() as session:
        await session.execute(
            update(Job).where(Job.id == job_id).values(**values)
        )
        await session.commit()


async def _publish(
    job_id: uuid.UUID,
    stage: str,
    pct: int,
    message: str,
    status: str = "processing",
    error: str | None = None,
) -> None:
    # This sends progress updates about a job to live listeners
    # It includes the stage, progress percentage, and any error messages
    event = ProgressEvent(
        job_id=str(job_id),
        stage=stage,
        progress_pct=pct,
        message=message,
        status=status,
        error=error,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
    )
    await publish_progress(str(job_id), event.model_dump())


# -------------------
# Base task class
# -------------------


class _BaseDocTask(Task):
    # Base class for all document processing tasks
    # Adds logging and makes sure tasks don't run twice accidentally

    abstract = True

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        """Log unhandled task failures with full traceback."""
        logger.error(
            "Task %s[%s] raised unhandled exception: %s",
            self.name,
            task_id,
            exc,
            exc_info=einfo.traceback,
        )

    def on_retry(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        """Log retry attempts with the delay before next execution."""
        logger.warning(
            "Task %s[%s] retrying due to: %s",
            self.name,
            task_id,
            exc,
        )


# ---------------------------------------------------------------------------
# Task: process_document
# ---------------------------------------------------------------------------


@celery_app.task(
    base=_BaseDocTask,
    name="app.workers.tasks.process_document",
    bind=True,
    queue="documents",
    # Retry on transient infrastructure errors only.
    # Pipeline-level failures are handled inside pipeline.run_pipeline().
    autoretry_for=(OSError, ConnectionError),
    retry_kwargs={"max_retries": 3},
    retry_backoff=True,
    retry_backoff_max=60,
    # Honour acks_late globally; each pipeline stage checkpoint is
    # idempotent so re-delivery after a crash is safe.
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_document(self: Task, job_id: str) -> dict[str, Any]:
    """
    Orchestrate the full document processing pipeline for a single job.

    This task is the *only* entry-point enqueued by
    :func:`~app.services.document_service.DocumentService.upload`.
    It delegates all stage logic to
    :func:`~app.workers.pipeline.run_pipeline`.

    Parameters
    ----------
    self:
        Bound Celery task instance (injected by ``bind=True``).
    job_id:
        String UUID of the :class:`~app.models.job.Job` row.

    Returns
    -------
    dict
        ``{"status": "completed", "job_id": job_id}`` on success.
        ``{"status": "cancelled", "job_id": job_id}`` if cancelled.
        ``{"status": "failed",    "job_id": job_id, "error": "..."}`` on failure.

    Raises
    ------
    Exception
        Re-raised after DB / Redis cleanup so Celery marks the task FAILURE
        and triggers ``on_failure``.
    """
    # Lazy import avoids circular dependency at module load time.
    from app.workers.pipeline import run_pipeline

    _job_id = uuid.UUID(job_id)
    logger.info("process_document started | job_id=%s | task_id=%s", job_id, self.request.id)

    # ------------------------------------------------------------------
    # 1. Idempotency guard — skip if job is already terminal
    # ------------------------------------------------------------------
    async def _check_status() -> JobStatus | None:
        async with async_session_factory() as session:
            row = await session.execute(
                select(Job.status).where(Job.id == _job_id)
            )
            result = row.scalar_one_or_none()
            return result

    current_status = _run(_check_status())
    if current_status is None:
        logger.error("Job %s not found in database — aborting task", job_id)
        return {"status": "failed", "job_id": job_id, "error": "job_not_found"}

    if current_status in (
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    ):
        logger.info(
            "Job %s is already terminal (%s) — skipping re-execution",
            job_id,
            current_status.value,
        )
        return {"status": current_status.value, "job_id": job_id}

    # ------------------------------------------------------------------
    # 2. Transition job → PROCESSING
    # ------------------------------------------------------------------
    _run(
        _mark_job(
            _job_id,
            JobStatus.PROCESSING,
            current_stage="starting",
            progress_pct=0,
        )
    )
    _run(_publish(_job_id, "starting", 0, "Pipeline starting"))

    # ------------------------------------------------------------------
    # 3. Pre-flight cancellation check
    # ------------------------------------------------------------------
    if _run(is_cancelled(job_id)):
        logger.info("Job %s cancelled before pipeline start", job_id)
        _run(_mark_job(_job_id, JobStatus.CANCELLED, current_stage="cancelled", progress_pct=0))
        _run(_publish(_job_id, "cancelled", 0, "Job cancelled before start", status="cancelled"))
        _run(clear_cancellation_flag(job_id))
        return {"status": "cancelled", "job_id": job_id}

    # ------------------------------------------------------------------
    # 4. Run the pipeline
    # ------------------------------------------------------------------
    try:
        result = _run(run_pipeline(