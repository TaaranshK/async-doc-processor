"""
Data models for result requests and responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ------
# Extracted data (the shape of what gets extracted from documents)
# ------

class FileMetadata(BaseModel):
    name: str
    type: str
    size: int


class ExtractedFields(BaseModel):
    # Structured fields extracted from a document

    title: str | None = None
    category: str | None = None
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    file_metadata: FileMetadata | None = None
    status: str | None = None
    extraction_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


# -------
# Response models
# -------

class ResultResponse(BaseModel):
    # The extracted data from a job

    id:               uuid.UUID
    job_id:           uuid.UUID
    raw_output:       ExtractedFields
    reviewed_output:  ExtractedFields | None
    is_finalized:     bool
    finalized_at:     datetime | None

    model_config = {"from_attributes": True}


# ------
# Request models
# ------

class ResultUpdateRequest(BaseModel):
    # Data the user sends to update the extracted results
    # Fields they don't include stay unchanged

    title: str | None = None
    category: str | None = None
    summary: str | None = None
    keywords: list[str] | None = None
    status: str | None = None
    extraction_confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    def to_partial_dict(self) -> dict:
        # Return only the fields the user actually set (skip the None ones)
        return {k: v for k, v in self.model_dump().items() if v is not None}


class ReviewedOutputUpdate(BaseModel):
    # Data the user sends to update reviewed output fields

    fields: dict = Field(default_factory=dict, description="Fields to merge into reviewed_output")
