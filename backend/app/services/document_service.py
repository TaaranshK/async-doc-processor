from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.job_model import JobStatus
from app.repositories.document_repository import DocumentRepository
from app.repositories.job_repository import JobRepository
from app.schemas.document_schema import DocumentUploadItem
from app.workers.job_worker import process_document_task

logger = get_logger(__name__)


class DocumentUploadError(RuntimeError):
    pass


class FileTooLargeError(ValueError):
    pass


class UnsupportedFileTypeError(ValueError):
    pass


class DocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._documents = DocumentRepository(db)
        self._jobs = JobRepository(db)

    async def upload_many(
        self,
        files: list[UploadFile],
        uploaded_by: uuid.UUID | None = None,
    ) -> list[DocumentUploadItem]:
        if not files:
            return []

        items: list[DocumentUploadItem] = []
        for file in files:
            items.append(await self.upload(file=file, uploaded_by=uploaded_by))
        return items

    async def upload(
        self,
        file: UploadFile,
        uploaded_by: uuid.UUID | None = None,
    ) -> DocumentUploadItem:
        content_type = file.content_type or "application/octet-stream"
        self._validate_mime_type(content_type)

        storage_path, size = await self._write_to_storage(file)
        self._validate_size(size)

        document = await self._documents.create(
            filename=file.filename or "upload",
            file_type=content_type,
            file_size=size,
            storage_path=storage_path,
            uploaded_by=uploaded_by,
        )
        job = await self._jobs.create(document_id=document.id)

        celery_result = process_document_task.apply_async(
            kwargs={"job_id": str(job.id)},
            queue="documents",
        )
        job.celery_task_id = celery_result.id
        job.status = JobStatus.QUEUED
        await self._db.commit()

        logger.info("job enqueued", extra={"job_id": str(job.id), "task_id": celery_result.id})

        return DocumentUploadItem(
            document_id=document.id,
            job_id=job.id,
            filename=document.filename,
            file_size=document.file_size,
        )

    def _validate_mime_type(self, content_type: str) -> None:
        if content_type not in settings.ALLOWED_MIME_TYPES:
            raise UnsupportedFileTypeError(f"Unsupported file type '{content_type}'.")

    def _validate_size(self, size: int) -> None:
        if size > settings.MAX_FILE_SIZE_BYTES:
            raise FileTooLargeError(
                f"File size {size} exceeds {settings.MAX_FILE_SIZE_BYTES} bytes."
            )

    async def _write_to_storage(self, file: UploadFile) -> tuple[str, int]:
        if settings.STORAGE_BACKEND != "local":
            raise DocumentUploadError("Only local storage is configured for v1.")

        storage_dir = Path(settings.LOCAL_STORAGE_PATH)
        storage_dir.mkdir(parents=True, exist_ok=True)

        safe_name = f"{uuid.uuid4()}_{Path(file.filename or 'upload').name}"
        destination = storage_dir / safe_name

        size = 0
        chunk_size = 1024 * 1024

        async with aiofiles.open(destination, "wb") as handle:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.MAX_FILE_SIZE_BYTES:
                    await handle.close()
                    destination.unlink(missing_ok=True)
                    raise FileTooLargeError(
                        f"File size {size} exceeds {settings.MAX_FILE_SIZE_BYTES} bytes."
                    )
                await handle.write(chunk)

        await file.close()
        return str(destination), size
