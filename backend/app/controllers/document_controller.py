from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middlewares.auth_middleware import OptionalUser
from app.schemas.document_schema import DocumentUploadBatchResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentUploadBatchResponse)
async def upload_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: OptionalUser,
    files: list[UploadFile] = File(...),
) -> DocumentUploadBatchResponse:
    service = DocumentService(db)
    items = await service.upload_many(files=files, uploaded_by=user.id if user else None)
    return DocumentUploadBatchResponse(items=items)
