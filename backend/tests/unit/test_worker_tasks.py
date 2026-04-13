from __future__ import annotations

import pytest

from app.models.document_model import Document
from app.models.job_model import Job, JobStatus
from app.models.result_model import Result
from app.workers.job_worker import _process_document_async


@pytest.mark.asyncio
async def test_worker_writes_result_only_on_completion(db_session, monkeypatch, tmp_path):
    file_path = tmp_path / "worker.txt"
    file_path.write_text("alpha beta gamma delta alpha", encoding="utf-8")

    document = Document(
        filename="worker.txt",
        file_type="text/plain",
        file_size=file_path.stat().st_size,
        storage_path=str(file_path),
    )
    db_session.add(document)
    await db_session.flush()

    job = Job(document_id=document.id, status=JobStatus.QUEUED, celery_task_id="task-1")
    db_session.add(job)
    await db_session.commit()

    published_events = []

    async def fake_publish(**kwargs):  # type: ignore[no-untyped-def]
        published_events.append(kwargs.get("event"))

    monkeypatch.setattr("app.workers.job_worker.publish_progress", fake_publish)

    await _process_document_async(job.id, "task-1")

    await db_session.refresh(job)
    stored_job = await db_session.get(Job, job.id)
    result = (
        await db_session.execute(
            __import__("sqlalchemy").select(Result).where(Result.job_id == job.id)
        )
    ).scalar_one()

    assert stored_job.status == JobStatus.COMPLETED
    assert result.raw_output["title"]
    assert published_events[-1] == "job_completed"


@pytest.mark.asyncio
async def test_stale_task_is_discarded(db_session, monkeypatch, tmp_path):
    file_path = tmp_path / "stale.txt"
    file_path.write_text("text", encoding="utf-8")

    document = Document(
        filename="stale.txt",
        file_type="text/plain",
        file_size=file_path.stat().st_size,
        storage_path=str(file_path),
    )
    db_session.add(document)
    await db_session.flush()

    job = Job(document_id=document.id, status=JobStatus.QUEUED, celery_task_id="expected-task")
    db_session.add(job)
    await db_session.commit()

    async def fail_publish(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("stale task should not publish progress")

    monkeypatch.setattr("app.workers.job_worker.publish_progress", fail_publish)

    await _process_document_async(job.id, "late-task")

    await db_session.refresh(job)
    stored_job = await db_session.get(Job, job.id)
    assert stored_job.status == JobStatus.QUEUED
