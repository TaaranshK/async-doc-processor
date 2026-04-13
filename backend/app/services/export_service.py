"""
Handles exporting results to JSON or CSV format.

You can export one result or many at once.
Only completed results can be exported.
"""

from __future__ import annotations

import csv
import io
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.logging import get_logger
from app.models.document import Document
from app.models.job import Job
from app.models.result import Result
from app.schemas.export import ExportRow

logger = get_logger(__name__)

# ----------
# Exceptions
# ----------

class ExportNotReadyError(ValueError):
    # Raised when trying to export a result that's not finished yet


# -------
# Service
# -------

class ExportService:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # --
    # Single export
    # --

    async def export_json(self, job_id: uuid.UUID) -> str:
        # Export one job's result as a JSON string
        result = await self._fetch_finalised(job_id)
        payload = {
            "job_id":      str(job_id),
            "document_id": str(result.job.document_id),
            "filename":    result.job.document.filename,
            "output":      result.effective_output,
            "finalized_at": result.finalized_at.isoformat() if result.finalized_at else None,
        }
        return json.dumps(payload, indent=2, default=str)

    async def export_csv(self, job_id: uuid.UUID) -> str:
        # Export one job's result as a CSV string
        result = await self._fetch_finalised(job_id)
        row = self._result_to_row(result)
        return self._rows_to_csv([row])

    # --
    # Bulk export
    # --

    async def bulk_export_json(self, job_ids: list[uuid.UUID]) -> str:
        # Export many jobs' results as one JSON array
        results = await self._fetch_bulk(job_ids)
        payload = []
        for result in results:
            payload.append({
                "job_id":       str(result.job_id),
                "document_id":  str(result.job.document_id),
                "filename":     result.job.document.filename,
                "output":       result.effective_output,
                "finalized_at": result.finalized_at.isoformat() if result.finalized_at else None,
            })
        return json.dumps(payload, indent=2, default=str)

    async def bulk_export_csv(self, job_ids: list[uuid.UUID]) -> str:
        # Export many jobs' results as one CSV with multiple rows
        results = await self._fetch_bulk(job_ids)
        rows = [self._result_to_row(r) for r in results]
        return self._rows_to_csv(rows)

    # --
    # Internal helpers
    # --

    async def _fetch_finalised(self, job_id: uuid.UUID) -> Result:
        # Get a completed result with all related data
        # Raises an error if the result doesn't exist or isn't finished
        row = await self._db.execute(
            select(Result)
            .options(
                joinedload(Result.job).joinedload(Job.document)
            )
            .where(Result.job_id == job_id)
        )
        result = row.scalar_one_or_none()

        if result is None:
            raise ExportNotReadyError(f"No result found for job {job_id}.")
        if not result.is_finalized:
            raise ExportNotReadyError(
                f"Result for job {job_id} is not yet finalised."
            )

        return result

    async def _fetch_bulk(self, job_ids: list[uuid.UUID]) -> list[Result]:
        # Get multiple completed results in one query
        # Skips any that don't exist or aren't finished
        rows = await self._db.execute(
            select(Result)
            .options(
                joinedload(Result.job).joinedload(Job.document)
            )
            .where(
                Result.job_id.in_(job_ids),
                Result.is_finalized.is_(True),
            )
        )
        results = rows.scalars().all()

        if len(results) < len(job_ids):
            found = {r.job_id for r in results}
            missing = [str(jid) for jid in job_ids if jid not in found]
            logger.warning(
                "some jobs skipped in bulk export (not found or not finalised)",
                extra={"skipped": missing},
            )

        return list(results)

    def _result_to_row(self, result: Result) -> ExportRow:
        """Flatten a Result into an ExportRow for CSV serialisation."""
        output = result.effective_output
        return ExportRow(
            job_id=str(result.job_id),
            document_id=str(result.job.document_id),
            filename=result.job.document.filename,
            title=output.get("title") or "",
            category=output.get("category") or "",
            summary=output.get("summary") or "",
            keywords=", ".join(output.get("keywords") or []),
            status=output.get("status") or "",
            extraction_confidence=str(output.get("extraction_confidence") or ""),
            finalized_at=result.finalized_at.isoformat() if result.finalized_at else "",
        )

    @staticmethod
    def _rows_to_csv(rows: list[ExportRow]) -> str:
        """Serialise a list of ExportRows to a CSV string."""
        if not rows:
            return ""

        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=list(ExportRow.model_fields.keys()),
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.model_dump())

        return buf.getvalue()