"""
Data models for document requests and responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    # All the info about an uploaded document

    id:           uuid.UUID
    filename:     str
    file_type:    str
    file_size:    int
    storage_path: str
    uploaded_by:  uuid.UUID | None
    created_at:   datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    # What we send back after someone uploads a file
    # Includes the document ID and the job ID that will process it

    document_id: uuid.UUID = Field(..., description="ID of the created document record.")
    job_id:      uuid.UUID = Field(..., description="ID of the queued processing job.")
    filename:    str
    file_size:   int


class DocumentUploadBatchResponse(BaseModel):
    items: list[DocumentUploadResponse]


# Alias for the internal service layer
DocumentUploadItem = DocumentUploadResponse
