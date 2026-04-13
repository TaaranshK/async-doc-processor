from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.export_service import ExportService

router = APIRouter(tags=["export"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/jobs/{job_id}/export")
async def export_job(
    job_id: UUID,
    db: DbSession,
    format: str = Query("json", pattern="^(json|csv)$"),
) -> Response:
    content, media_type = await ExportService(db).export_job(job_id, format)
    filename = f"job-{job_id}.{format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
        status_code=status.HTTP_200_OK,
    )


@router.get("/export/bulk")
async def export_bulk(
    db: DbSession,
    ids: list[str] = Query(..., description="Job IDs (comma-separated or repeated)"),
    format: str = Query("json", pattern="^(json|csv)$"),
) -> Response:
    raw_ids: list[str] = []
    for value in ids:
        raw_ids.extend([part.strip() for part in value.split(",") if part.strip()])
    try:
        job_ids = [UUID(raw) for raw in raw_ids]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid job id: {exc}") from exc
    content, media_type = await ExportService(db).export_bulk(job_ids, format)
    filename = f"bulk-export.{format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
        status_code=status.HTTP_200_OK,
    )
