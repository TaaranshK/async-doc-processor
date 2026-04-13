from __future__ import annotations

import pytest

from app.models.document import Document
from app.models.job import Job, JobStatus
from app.models.result import Result
from app.services.export_service import ExportNotReadyError, ExportService


@pytest.mark.asyncio
async def test_export_job_json_requires_finalized_result(db_session):
    document = Document(
        filename="doc.txt",
        file_type="text/plain",
        file_size=20,
        storage_path="doc.txt",
    )
    db_session.add(document)
    await db_session.flush()

    job = Job(document_id=document.id, status=JobStatus.COMPLETED)
    db_session.add(job)
    await db_session.flush()

    result = Result(
        job_id=job.id,
        raw_output={"title": "Hello"},
        reviewed_output={"title": "Hello"},
        is_finalized=False,
    )
    db_session.add(result)
    await db_session.commit()

    service = ExportService(db_session)
    with pytest.raises(ExportNotReadyError):
        await service.export_job(job.id, "json")


@pytest.mark.asyncio
async def test_export_bulk_csv_returns_rows(db_session):
    document = Document(
        filename="doc.txt",
        file_type="text/plain",
        file_size=20,
        storage_path="doc.txt",
    )
    db_session.add(document)
    await db_session.flush()

    job = Job(document_id=document.id, status=JobStatus.COMPLETED)
    db_session.add(job)
    await db_session.flush()

    result = Result(
        job_id=job.id,
        raw_output={"title": "Hello", "keywords": ["hello"]},
        reviewed_output={"title": "Hello", "keywords": ["hello"]},
        is_finalized=True,
    )
    db_session.add(result)
    await db_session.commit()

    service = ExportService(db_session)
    content, media_type = await service.export_bulk([job.id], "csv")

    assert media_type == "text/csv"
    assert "job_id" in content
    assert "Hello" in content
