"""
Data models for job requests and responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.job_model import JobStatus


# -------
# Response models (data sent back to the user)
# -------

class JobSummary(BaseModel):
    # One job in a list (dashboard view)

    id:            uuid.UUID
    document_id:   uuid.UUID
    filename:      str
    file_type:     str
    file_size:     int
    status:        JobStatus
    progress_pct:  int = Field(ge=0, le=100)
    current_stage: str | None
    retry_count:   int
    error_message: str | None
    created_at:    datetime
    updated_at:    datetime

    model_config = {"from_attributes": True}


class JobDetailResponse(BaseModel):
    # All the details about one job

    id:              uuid.UUID
    document_id:     uuid.UUID
    filename:        str
    file_type:       str
    file_size:       int
    status:          JobStatus
    celery_task_id:  str | None
    current_stage:   str | None
    progress_pct:    int = Field(ge=0, le=100)
    error_message:   str | None
    retry_count:     int
    created_at:      datetime
    updated_at:      datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    # A page of jobs

    items:     list[JobSummary]
    total:     int
    page:      int
    page_size: int


# ------
# Query parameters
# ------

class JobFilterParams(BaseModel):
    # Options for filtering and searching the jobs list

    status:   list[JobStatus] | None = Field(
        default=None,
        description="Filter by one or more statuses.",
    )
    search:   str | None = Field(
        default=None,
        max_length=255,
        description="Free-text search on the document filename.",
    )
    page:       int = Field(default=1, ge=1)
    page_size:  int = Field(default=20, ge=1, le=100)
    sort_by:    str = Field(
        default="created_at",
        pattern="^(created_at|status)$",
        description="Field to sort by.",
    )
    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
    )

    @field_validator("status", mode="before")
    @classmethod
    def _split_status(cls, value):  # type: ignore[override]
        if value is None:
            return value
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value
