from __future__ import annotations

import json
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProgressEvent(BaseModel):
    event: str = Field(..., examples=["extraction_started"])
    job_id: uuid.UUID
    stage: str = Field(..., examples=["extraction_started"])
    progress_pct: int = Field(..., ge=0, le=100)
    timestamp: datetime
    metadata: dict = Field(default_factory=dict)

    def to_sse(self) -> str:
        data = self.model_dump(mode="json")
        return f"event: {self.event}\ndata: {json.dumps(data)}\n\n"
