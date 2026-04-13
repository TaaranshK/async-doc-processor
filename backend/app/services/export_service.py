from __future__ import annotations

import csv
import io
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.logging import get_logger
from app.models.document_model import Document
from app.models.job_model import Job
from app.models.result_model import Result

logger = get_logger(__name__)


class ExportNotReadyError(ValueError):
    pass


class ExportService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def export_job(self, job_id: uuid.UUID, fmt: str) -> tuple[str, str]:
        if fmt == "csv":
            return await self._export_csv(job_id)
        return await self._export_json(job_id)

    async def export_bulk(self, job_ids: list[uuid.UUID], fmt: str) -> tuple[str, str]:
        if fmt == "csv":
            return await self._export_bulk_csv(job_ids)
        return await self._export_bulk_json(job_ids)

    async def _fetch_finalized(self, job_id: uuid.UUID) -> Result:
        row = await self._db.execute(
            select(Result)
            .options(joinedload(Result.job).joinedload(Job.document))
            .where(Result.job_id == job_id)
        )
        result = row.scalar_one_or_none()
        if result is None:
            raise ExportNotReadyError(f"No result found for job {job_id}.")
        if not result.is_finalized:
            raise ExportNotReadyError(f"Result for job {job_id} is not finalized.")
        return result

    async def _fetch_bulk(self, job_ids: list[uuid.UUID]) -> list[Result]:
        rows = await self._db.execute(
            select(Result)
            .options(joinedload(Result.job).joinedload(Job.document))
            .where(Result.job_id.in_(job_ids), Result.is_finalized.is_(True))
        )
        results = rows.scalars().all()
        return list(results)

    async def _export_json(self, job_id: uuid.UUID) -> tuple[str, str]:
        result = await self._fetch_finalized(job_id)
        payload = {
            "job_id": str(job_id),
            "document_id": str(result.job.document_id),
            "filename": result.job.document.filename,
            "output": result.effective_output,
            "finalized_at": result.finalized_at.isoformat() if result.finalized_at else None,
        }
        return json.dumps(payload, indent=2, default=str), "application/json"

    async def _export_csv(self, job_id: uuid.UUID) -> tuple[str, str]:
        result = await self._fetch_finalized(job_id)
        return self._rows_to_csv([self._result_to_row(result)]), "text/csv"

    async def _export_bulk_json(self, job_ids: list[uuid.UUID]) -> tuple[str, str]:
        results = await self._fetch_bulk(job_ids)
        payload = [
            {
                "job_id": str(result.job_id),
                "document_id": str(result.job.document_id),
                "filename": result.job.document.filename,
                "output": result.effective_output,
                "finalized_at": result.finalized_at.isoformat() if result.finalized_at else None,
            }
            for result in results
        ]
        return json.dumps(payload, indent=2, default=str), "application/json"

    async def _export_bulk_csv(self, job_ids: list[uuid.UUID]) -> tuple[str, str]:
        results = await self._fetch_bulk(job_ids)
        rows = [self._result_to_row(r) for r in results]
        return self._rows_to_csv(rows), "text/csv"

    def _result_to_row(self, result: Result) -> dict[str, str]:
        output = result.effective_output or {}
        return {
            "job_id": str(result.job_id),
            "document_id": str(result.job.document_id),
            "filename": result.job.document.filename,
            "title": output.get("title") or "",
            "category": output.get("category") or "",
            "summary": output.get("summary") or "",
            "keywords": ", ".join(output.get("keywords") or []),
            "status": output.get("status") or "",
            "extraction_confidence": str(output.get("extraction_confidence") or ""),
            "finalized_at": result.finalized_at.isoformat() if result.finalized_at else "",
        }

    @staticmethod
    def _rows_to_csv(rows: list[dict[str, str]]) -> str:
        if not rows:
            return ""

        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=list(rows[0].keys()),
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buf.getvalue()
