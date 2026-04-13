from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.result_model import Result


class ResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_job(self, job_id: uuid.UUID) -> Result | None:
        result = await self._session.execute(select(Result).where(Result.job_id == job_id))
        return result.scalar_one_or_none()

    async def upsert_raw_output(self, job_id: uuid.UUID, raw_output: dict) -> Result:
        existing = await self.get_by_job(job_id)
        if existing is not None:
            await self._session.execute(
                update(Result).where(Result.job_id == job_id).values(raw_output=raw_output)
            )
            await self._session.flush()
            return existing

        result = Result(job_id=job_id, raw_output=raw_output)
        self._session.add(result)
        await self._session.flush()
        return result

    async def update_reviewed_output(self, job_id: uuid.UUID, reviewed_output: dict) -> None:
        await self._session.execute(
            update(Result).where(Result.job_id == job_id).values(reviewed_output=reviewed_output)
        )
