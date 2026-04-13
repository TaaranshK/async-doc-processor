from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document import Document
from app.models.job import Job, JobStatus
from app.schemas.document import DocumentUploadItem

logger = get_logger(__name__)


class FileTooLargeError(ValueError):
    pass


class UnsupportedFileTypeError(ValueError):
    pass


class DocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def upload_many(
        self,
        files: list[UploadFile],
        uploaded_by: uuid.UUID | None = None,
    ) -> list[DocumentUploadItem]:
        responses: list[DocumentUploadItem] = []
        for file in files:
            responses.append(await self.upload(file=file, uploaded_by=uploaded_by))
        return responses

    async def upload(
        self,
        file: UploadFile,
        uploaded_by: uuid.UUID | None = None,
    ) -> DocumentUploadItem:
        content_type = file.content_type or "application/octet-stream"
        self._validate_mime_type(content_type)

        data = await file.read()
        self._validate_size(len(data))

        storage_path = await self._write_to_storage(
            data=data,
            filename=file.filename or "upload",
            content_type=content_type,
        )

        document = Document(
            filename=file.filename or "upload",
            file_type=content_type,
            file_size=len(data),
            storage_path=storage_path,
            uploaded_by=uploaded_by,
        )
        self._db.add(document)
        await self._db.flush()

        job = Job(
            document_id=document.id,
            status=JobStatus.QUEUED,
            progress_pct=0,
            current_stage="queued",
        )
        self._db.add(job)
        await self._db.flush()

        from app.workers.tasks import process_document

        task = process_document.apply_async(
            kwargs={"job_id": str(job.id), "document_id": str(document.id)},
            queue="documents",
        )
        job.celery_task_id = task.id
        await self._db.commit()
        await self._db.refresh(job)

        logger.info("job enqueued", extra={"job_id": str(job.id), "task_id": task.id})

        return DocumentUploadItem(
            document_id=document.id,
            job_id=job.id,
            filename=document.filename,
            file_size=document.file_size,
        )

    async def get_document(self, document_id: uuid.UUID) -> Document | None:
        result = await self._db.execute(
            select(Document)
            .options(joinedload(Document.jobs))
            .where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    def _validate_mime_type(self, content_type: str) -> None:
        if content_type not in settings.ALLOWED_MIME_TYPES:
            raise UnsupportedFileTypeError(
                f"Unsupported file type '{content_type}'."
            )

    def _validate_size(self, size: int) -> None:
        if size > settings.MAX_FILE_SIZE_BYTES:
            raise FileTooLargeError(
                f"File size {size} exceeds {settings.MAX_FILE_SIZE_BYTES} bytes."
            )

    async def _write_to_storage(self, data: bytes, filename: str, content_type: str) -> str:
        if settings.STORAGE_BACKEND == "s3":
            return await self._write_s3(data, filename, content_type)
        return await self._write_local(data, filename)

    async def _write_local(self, data: bytes, filename: str) -> str:
        import aiofiles

        storage_dir = Path(settings.LOCAL_STORAGE_PATH)
        storage_dir.mkdir(parents=True, exist_ok=True)

        safe_name = f"{uuid.uuid4()}_{Path(filename).name}"
        destination = storage_dir / safe_name
        chunk_size = 1024 * 1024

        async with aiofiles.open(destination, "wb") as handle:
            if len(data) > settings.CHUNKED_WRITE_THRESHOLD_BYTES:
                for index in range(0, len(data), chunk_size):
                    await handle.write(data[index : index + chunk_size])
            else:
                await handle.write(data)
        return str(destination)

    async def _write_s3(self, data: bytes, filename: str, content_type: str) -> str:
        import aioboto3  # type: ignore

        key = f"uploads/{uuid.uuid4()}_{Path(filename).name}"
        session = aioboto3.Session()
        async with session.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        ) as client:
            await client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        return key
