from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.job_model import Job, JobStatus
from app.models.result_model import Result
from app.workers.job_worker import _process_document_async


@pytest.mark.asyncio
async def test_upload_creates_job(client, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.workers.job_worker.process_document_task.apply_async",
        lambda *args, **kwargs: SimpleNamespace(id="queued-task"),
    )

    response = await client.post(
        "/api/v1/documents/upload",
        files=[("files", ("sample.txt", io.BytesIO(b"hello world"), "text/plain"))],
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1

    job_id = payload["items"][0]["job_id"]
    job = await db_session.get(Job, job_id)
    assert job.status == JobStatus.QUEUED


@pytest.mark.asyncio
async def test_processing_to_completion_finalize_and_export(client, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.workers.job_worker.process_document_task.apply_async",
        lambda *args, **kwargs: SimpleNamespace(id="queued-task"),
    )
    async def noop_publish(**kwargs):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr("app.workers.job_worker.publish_progress", noop_publish)

    upload_response = await client.post(
        "/api/v1/documents/upload",
        files=[("files", ("sample.txt", io.BytesIO(b"hello world again"), "text/plain"))],
    )
    job_id = upload_response.json()["items"][0]["job_id"]

    job = await db_session.get(Job, job_id)
    await _process_document_async(job.id, "queued-task")

    result_response = await client.get(f"/api/v1/jobs/{job_id}/result")
    assert result_response.status_code == 200

    finalize_response = await client.post(f"/api/v1/jobs/{job_id}/finalize")
    assert finalize_response.status_code == 200

    export_response = await client.get(f"/api/v1/jobs/{job_id}/export", params={"format": "json"})
    assert export_response.status_code == 200
    assert "title" in export_response.text


@pytest.mark.asyncio
async def test_retry_flow(client, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.workers.job_worker.process_document_task.apply_async",
        lambda *args, **kwargs: SimpleNamespace(id="retry-task"),
    )

    upload_response = await client.post(
        "/api/v1/documents/upload",
        files=[("files", ("sample.txt", io.BytesIO(b"retry me"), "text/plain"))],
    )
    job_id = upload_response.json()["items"][0]["job_id"]

    job = await db_session.get(Job, job_id)
    job.status = JobStatus.FAILED
    job.current_stage = "failed"
    job.error_message = "temporary error"
    await db_session.commit()

    response = await client.post(f"/api/v1/jobs/{job_id}/retry")
    assert response.status_code == 200
    assert response.json()["celery_task_id"] == "retry-task"


@pytest.mark.asyncio
async def test_cancel_flow(client, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.workers.job_worker.process_document_task.apply_async",
        lambda *args, **kwargs: SimpleNamespace(id="cancel-task"),
    )
    async def noop_publish(**kwargs):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr("app.services.job_service.publish_progress", noop_publish)

    upload_response = await client.post(
        "/api/v1/documents/upload",
        files=[("files", ("sample.txt", io.BytesIO(b"cancel me"), "text/plain"))],
    )
    job_id = upload_response.json()["items"][0]["job_id"]

    response = await client.post(f"/api/v1/jobs/{job_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_bulk_export_returns_finalized_records(client, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.workers.job_worker.process_document_task.apply_async",
        lambda *args, **kwargs: SimpleNamespace(id="bulk-task"),
    )
    async def noop_publish(**kwargs):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr("app.workers.job_worker.publish_progress", noop_publish)

    upload_response = await client.post(
        "/api/v1/documents/upload",
        files=[("files", ("sample.txt", io.BytesIO(b"bulk export"), "text/plain"))],
    )
    job_id = upload_response.json()["items"][0]["job_id"]

    job = await db_session.get(Job, job_id)
    await _process_document_async(job.id, "bulk-task")
    await client.post(f"/api/v1/jobs/{job_id}/finalize")

    response = await client.get("/api/v1/export/bulk", params={"ids": [job_id], "format": "csv"})
    assert response.status_code == 200
    assert "job_id" in response.text
