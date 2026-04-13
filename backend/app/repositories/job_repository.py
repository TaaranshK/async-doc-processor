from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_model import Document
from app.models.job_model import Job, JobStatus


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, job_id: uuid.UUID) -> Job | None:
        result = await self._session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def get_with_document(self, job_id: uuid.UUID) -> Job | None:
        result = await self._session.execute(
            select(Job).join(Job.document).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def create(self, *, document_id: uuid.UUID) -> Job:
        job = Job(
            document_id=document_id,
            status=JobStatus.QUEUED,
            progress_pct=0,
            current_stage="queued",
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def update_status(
        self,
        *,
        job_id: uuid.UUID,
        status: JobStatus,
        current_stage: str | None = None,
        progress_pct: int | None = None,
        error_message: str | None = None,
    ) -> None:
        values: dict = {"status": status}
        if current_stage is not None:
            values["current_stage"] = current_stage
        if progress_pct is not None:
            values["progress_pct"] = progress_pct
        if error_message is not None:
            values["error_message"] = error_message
        await self._session.execute(update(Job).where(Job.id == job_id).values(**values))

    async def list_jobs(
        self,
        *,
        search: str | None,
        statuses: list[JobStatus] | None,
        sort_by: str,
        sort_order: str,
        offset: int,
        limit: int,
    ) -> tuple[list[tuple[Job, Document]], int]:
        query = select(Job, Document).join(Document, Job.document_id == Document.id)

        if statuses:
            query = query.where(Job.status.in_(statuses))
        if search:
            query = query.where(Document.filename.ilike(f"%{search}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one()

        sort_column = Job.created_at if sort_by == "created_at" else Job.status
        if sort_order == "desc":
            sort_column = sort_column.desc()
        query = query.order_by(sort_column).offset(offset).limit(limit)

        rows = (await self._session.execute(query)).all()
        return rows, total
