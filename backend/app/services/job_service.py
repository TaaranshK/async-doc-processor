from __future__ import annotations

import math
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import clear_cancellation_flag, set_cancellation_flag
from app.models.document import Document
from app.models.job import Job, JobStatus
from app.schemas.job import JobFilterParams, JobListItem, JobListResponse, JobResponse

logger = get_logger(__name__)


class JobNotFoundError(LookupError):
    pass


class InvalidStatusTransitionError(ValueError):
    pass


class JobService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_job(self, job_id: uuid.UUID) -> Job:
        result = await self._db.execute(
            select(Job).options(joinedload(Job.document)).where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found.")
        return job

    async def get_job_with_result(self, job_id: uuid.UUID) -> Job:
        result = await self._db.execute(
            select(Job)
            .options(joinedload(Job.document), joinedload(Job.result))
            .where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found.")
        return job

    async def list_jobs(self, params: JobFilterParams) -> JobListResponse:
        query = select(Job, Document.filename).join(Document, Job.document_id == Document.id)

        if params.status:
            query = query.where(Job.status.in_(params.status))
        if params.search:
            query = query.where(Document.filename.ilike(f"%{params.search}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._db.execute(count_query)).scalar_one()

        sort_column = Job.created_at if params.order_by == "created_at" else Job.status
        if params.order == "desc":
            sort_column = sort_column.desc()

        offset = (params.page - 1) * params.size
        rows = (
            await self._db.execute(query.order_by(sort_column).offset(offset).limit(params.size))
        ).all()

        items = [
            JobListItem(
                id=job.id,
                document_id=job.document_id,
                filename=filename,
                status=job.status,
                progress_pct=job.progress_pct,
                current_stage=job.current_stage,
                retry_count=job.retry_count,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
            for job, filename in rows
        ]

        return JobListResponse(
            items=items,
            total=total,
            page=params.page,
            size=params.size,
            pages=math.ceil(total / params.size) if total else 0,
        )

    async def update_progress(
        self,
        job_id: uuid.UUID,
        status: JobStatus,
        stage: str,
        progress_pct: int,
        error_message: str | None = None,
    ) -> None:
        values: dict = {
            "status": status,
            "current_stage": stage,
            "progress_pct": max(0, min(100, progress_pct)),
        }
        if error_message is not None:
            values["error_message"] = error_message

        await self._db.execute(update(Job).where(Job.id == job_id).values(**values))
        await self._db.commit()

    async def retry_job(self, job_id: uuid.UUID) -> JobResponse:
        job = await self.get_job(job_id)
        if job.status != JobStatus.FAILED:
            raise InvalidStatusTransitionError("Only failed jobs can be retried.")
        if job.retry_count >= settings.CELERY_MAX_RETRIES:
            raise InvalidStatusTransitionError("Job reached the retry limit.")

        from app.workers.tasks import process_document

        task = process_document.apply_async(
            kwargs={"job_id": str(job.id), "document_id": str(job.document_id)},
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
        return JobResponse.model_validate(await self.get_job(job_id))

    async def cancel_job(self, job_id: uuid.UUID) -> JobResponse:
        job = await self.get_job(job_id)
        if job.is_terminal:
            raise InvalidStatusTransitionError("Terminal jobs cannot be cancelled.")

        await set_cancellation_flag(job_id)
        if job.celery_task_id:
            from app.workers.celery_app import celery_app

            celery_app.control.revoke(job.celery_task_id, terminate=True)

        await self._db.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(status=JobStatus.CANCELLED, current_stage="cancelled")
        )
        await self._db.commit()
        return JobResponse.model_validate(await self.get_job(job_id))
