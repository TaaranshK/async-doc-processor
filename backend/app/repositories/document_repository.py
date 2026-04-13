from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_model import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, document_id: uuid.UUID) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
        uploaded_by: uuid.UUID | None,
    ) -> Document:
        document = Document(
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=storage_path,
            uploaded_by=uploaded_by,
        )
        self._session.add(document)
        await self._session.flush()
        return document
