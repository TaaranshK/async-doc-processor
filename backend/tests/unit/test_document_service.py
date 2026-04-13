from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.models.document import Document
from app.models.job import Job, JobStatus
from app.services.document_service import DocumentService, FileTooLargeError


@pytest.mark.asyncio
async def test_upload_creates_document_and_job(db_session, monkeypatch, tmp_path):
    async def fake_write_to_storage(self, data: bytes, filename: str, content_type: str) -> str:
        return str(tmp_path / filename)

    def fake_apply_async(*args, **kwargs):
        return SimpleNamespace(id="celery-task-1")

    monkeypatch.setattr(DocumentService, "_write_to_storage", fake_write_to_storage)
    monkeypatch.setattr("app.workers.tasks.process_document.apply_async", fake_apply_async)

    upload_file = UploadFile(
        filename="sample.txt",
        file=__import__("io").BytesIO(b"hello async processing"),
        headers=Headers({"content-type": "text/plain"}),
    )

    service = DocumentService(db_session)
    response = await service.upload(upload_file)

    document = await db_session.get(Document, response.document_id)
    job = await db_session.get(Job, response.job_id)

    assert document is not None
    assert job is not None
    assert job.status == JobStatus.QUEUED
    assert job.celery_task_id == "celery-task-1"


@pytest.mark.asyncio
async def test_upload_rejects_large_file(db_session, monkeypatch):
    service = DocumentService(db_session)
    monkeypatch.setattr("app.services.document_service.settings.MAX_FILE_SIZE_BYTES", 5)

    upload_file = UploadFile(
        filename="too-large.txt",
        file=__import__("io").BytesIO(b"123456"),
        headers=Headers({"content-type": "text/plain"}),
    )

    with pytest.raises(FileTooLargeError):
        await service.upload(upload_file)
