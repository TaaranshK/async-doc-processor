"""
Data models for exporting results.\n"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class BulkExportRequest(BaseModel):
    # Request to export multiple jobs at once

    ids:    list[uuid.UUID] = Field(..., min_length=1, max_length=100)
    format: Literal["json", "csv"] = "json"


class ExportRow(BaseModel):
    # One row in a CSV export (all data converted to strings)

    job_id:               str
    document_id:          str
    filename:             str
    title:                str
    category:             str
    summary:              str
    keywords:             str   # comma-joined list
    status:               str
    extraction_confidence: str
    finalized_at:         str