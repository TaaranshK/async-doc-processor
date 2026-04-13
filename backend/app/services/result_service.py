from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.job import Job, JobStatus
from app.models.result import Result
from app.schemas.result import ResultResponse, ResultUpdateRequest


class ResultNotFoundError(LookupError):
    pass


class ResultAlreadyFinalizedError(ValueError):
    pass


class JobNotCompletedError(ValueError):
    pass


class ResultService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_result(self, job_id: uuid.UUID) -> Result:
        row = await self._db.execute(
            select(Result).options(joinedload(Result.job)).where(Result.job_id == job_id)
        )
        result = row.scalar_one_or_none()
        if result is None:
            raise ResultNotFoundError(f"Result for job {job_id} does not exist.")
        return result

    async def update_result(
        self,
        job_id: uuid.UUID,
        payload: ResultUpdateRequest,
    ) -> ResultResponse:
        result = await self.get_result(job_id)
        if result.is_finalized:
            raise ResultAlreadyFinalizedError("Finalized results are read-only.")

        updates = payload.to_partial_dict()
        if not updates:
            return ResultResponse.model_validate(result)

        merged = {**(result.reviewed_output or result.raw_output or {}), **updates}
        await self._db.execute(
            update(Result).where(Result.job_id == job_id).values(reviewed_output=merged)
        )
        await self._db.commit()
        return ResultResponse.model_validate(await self.get_result(job_id))

    async def finalize_result(self, job_id: uuid.UUID) -> ResultResponse:
        result = await self.get_result(job_id)
        if result.is_finalized:
            raise ResultAlreadyFinalizedError("Result is already finalized.")

        status = (
            await self._db.execute(select(Job.status).where(Job.id == job_id))
        ).scalar_one_or_none()
        if status != JobStatus.COMPLETED:
            raise JobNotCompletedError("Job must be completed before finalize.")

        await self._db.execute(
            update(Result)
            .where(Result.job_id == job_id)
            .values(is_finalized=True, finalized_at=datetime.now(timezone.utc))
        )
        await self._db.commit()
        return ResultResponse.model_validate(await self.get_result(job_id))
