"""
Models for progress updates sent to the user while processing.\n\"\"\"

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProgressEvent(BaseModel):
    # A progress update event sent while a job is processing
    # Shows what stage we're on and how far along we are

    event:        str      = Field(..., examples=["extraction_started"])
    job_id:       uuid.UUID
    stage:        str      = Field(..., examples=["extraction_started"])
    progress_pct: int      = Field(..., ge=0, le=100)
    timestamp:    datetime
    metadata:     dict     = Field(default_factory=dict)

    def to_sse(self) -> str:
        # Format this as a server-sent event that the browser can read
        import json
        data = self.model_dump(mode="json")
        return f"event: {self.event}\ndata: {json.dumps(data)}\n\n"