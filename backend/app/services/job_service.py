from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import clear_cancellation_flag, publish_progress, set_cancellation_flag
from app.models.document_model import Document
from app.models.job_model import Job, JobStatus
from app.repositories.job_repository import JobRepository
from app.schemas.job_schema import JobDetailResponse, JobFilterParams, JobListResponse, JobSummary
from app.workers.celery_app import celery_app
from app.workers.job_worker import process_document_task

logger = get_logger(__name__)


class JobNotFoundError(LookupError):
    pass


class InvalidStatusTransitionError(ValueError):
    pass


class JobService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._jobs = JobRepository(db)

    async def get_job(self, job_id: uuid.UUID) -> Job:
        job = await self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found.")
        return job

    async def get_job_detail(self, job_id: uuid.UUID) -> JobDetailResponse:
        row = await self._db.execute(
            select(Job, Document).join(Document, Job.document_id == Document.id).where(Job.id == job_id)
        )
        result = row.first()
        if result is None:
            raise JobNotFoundError(f"Job {job_id} not found.")
        job, document = result
        return JobDetailResponse(
            id=job.id,
            document_id=job.document_id,
            filename=document.filename,
            file_type=document.file_type,
            file_size=document.file_size,
            status=job.status,
            celery_task_id=job.celery_task_id,
            current_stage=job.current_stage,
            progress_pct=job.progress_pct,
            error_message=job.error_message,
            retry_count=job.retry_count,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    async def list_jobs(self, params: JobFilterParams) -> JobListResponse:
        offset = (params.page - 1) * params.page_size
        rows, total = await self._jobs.list_jobs(
            search=params.search,
            statuses=params.status,
            sort_by=params.sort_by,
            sort_order=params.sort_order,
            offset=offset,
            limit=params.page_size,
        )

        items = [
            JobSummary(
                id=job.id,
                document_id=job.document_id,
                filename=document.filename,
                file_type=document.file_type,
                file_size=document.file_size,
                status=job.status,
                progress_pct=job.progress_pct,
                current_stage=job.current_stage,
                retry_count=job.retry_count,
                error_message=job.error_message,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
            for job, document in rows
        ]

        return JobListResponse(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def retry_job(self, job_id: uuid.UUID) -> JobDetailResponse:
        job = await self.get_job(job_id)
        if job.status != JobStatus.FAILED:
            raise InvalidStatusTransitionError("Only failed jobs can be retried.")
        if job.retry_count >= settings.CELERY_MAX_RETRIES:
            raise InvalidStatusTransitionError("Job reached the retry limit.")

        task = process_document_task.apply_async(
            kwargs={"job_id": str(job.id)},
            queue="documents",
        )

        await clear_cancellation_flag(job_id)
        await self._db.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                celery_task_id=task.id,
                status=JobStatus.QUEUED,
                progress_pct=0,
                current_stage="queued",
                error_message=None,
                retry_count=job.retry_count + 1,
            )
        )
        await self._db.commit()
        return await self.get_job_detail(job_id)

    async def cancel_job(self, job_id: uuid.UUID) -> JobDetailResponse:
        job = await self.get_job(job_id)
        if job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            raise InvalidStatusTransitionError("Terminal jobs cannot be cancelled.")

        await set_cancellation_flag(job_id)
        if job.celery_task_id:
            celery_app.control.revoke(job.celery_task_id, terminate=True, signal="SIGTERM")
            logger.info("Celery task revoked", extra={"job_id": str(job.id), "task_id": job.celery_task_id})

        await self._db.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(status=JobStatus.CANCELLED, current_stage="job_cancelled")
        )
        await self._db.commit()
        await publish_progress(
            job_id=job_id,
            event="job_cancelled",
            stage="job_cancelled",
            progress_pct=job.progress_pct,
            metadata={"reason": "cancelled_by_user"},
        )
        return await self.get_job_detail(job_id)
