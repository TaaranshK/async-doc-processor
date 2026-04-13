from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.models.document import Document
from app.models.job import Job, JobStatus
from app.services.job_service import InvalidStatusTransitionError, JobService


@pytest.mark.asyncio
async def test_retry_job_resets_progress_and_assigns_new_task_id(db_session, monkeypatch):
    document = Document(
        filename="failed.txt",
        file_type="text/plain",
        file_size=10,
        storage_path="failed.txt",
    )
    db_session.add(document)
    await db_session.flush()

    job = Job(
        document_id=document.id,
        status=JobStatus.FAILED,
        progress_pct=70,
        current_stage="failed",
        retry_count=1,
        celery_task_id="old-task",
        error_message="boom",
    )
    db_session.add(job)
    await db_session.commit()

    monkeypatch.setattr(
        "app.workers.tasks.process_document.apply_async",
        lambda *args, **kwargs: SimpleNamespace(id="new-task"),
    )

    service = JobService(db_session)
    response = await service.retry_job(job.id)

    assert response.status == JobStatus.QUEUED
    assert response.progress_pct == 0
    assert response.celery_task_id == "new-task"
    assert response.retry_count == 2


@pytest.mark.asyncio
async def test_cancel_terminal_job_is_rejected(db_session):
    document = Document(
        filename="done.txt",
        file_type="text/plain",
        file_size=10,
        storage_path="done.txt",
    )
    db_session.add(document)
    await db_session.flush()

    job = Job(document_id=document.id, status=JobStatus.COMPLETED)
    db_session.add(job)
    await db_session.commit()

    service = JobService(db_session)
    with pytest.raises(InvalidStatusTransitionError):
        await service.cancel_job(job.id)
