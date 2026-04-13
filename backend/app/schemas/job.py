"""
Data models for job requests and responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.job import JobStatus


# -------
# Response models (data sent back to the user)
# -------

class JobResponse(BaseModel):
    # All the details about one job

    id:              uuid.UUID
    document_id:     uuid.UUID
    status:          JobStatus
    celery_task_id:  str | None
    current_stage:   str | None
    progress_pct:    int = Field(ge=0, le=100)
    error_message:   str | None
    retry_count:     int
    created_at:      datetime
    updated_at:      datetime

    model_config = {"from_attributes": True}


# Alias for detail view
JobDetailResponse = JobResponse


class JobListItem(BaseModel):
    # One job in a list (with just the important info for the dashboard)

    id:            uuid.UUID
    document_id:   uuid.UUID
    filename:      str           # taken from the document table
    status:        JobStatus
    progress_pct:  int = Field(ge=0, le=100)
    current_stage: str | None
    retry_count:   int
    created_at:    datetime
    updated_at:    datetime

    model_config = {"from_attributes": True}


# Alias for job summary in lists
JobSummary = JobListItem


class JobListResponse(BaseModel):
    # A page of jobs

    items:   list[JobListItem]
    total:   int
    page:    int
    size:    int
    pages:   int


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
    page:     int = Field(default=1, ge=1)
    size:     int = Field(default=20, ge=1, le=100)
    order_by: str = Field(
        default="created_at",
        pattern="^(created_at|status)$",
        description="Field to sort by.",
    )
    order:    str = Field(
        default="desc",
        pattern="^(asc|desc)$",
    )