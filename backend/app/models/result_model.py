"""
Stores the results after a document is successfully processed.

raw_output is what the AI extracted from the document.
reviewed_output is what the user edited and approved.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey


class Result(Base, UUIDPrimaryKey):
    __tablename__ = "results"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # each job has exactly one result
        index=True,
    )

    # The extraction as it came from the AI
    raw_output: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # The extraction after the user reviewed and edited it
    reviewed_output: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=None
    )

    # Has the user finalized this result?
    is_finalized: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # When did the user mark it as finalized?
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Link back to the job
    job: Mapped["Job"] = relationship(  # noqa: F821
        "Job",
        back_populates="result",
        lazy="raise",
    )

    @property
    def effective_output(self) -> dict:
        # Return the reviewed version if available, otherwise the original
        return self.reviewed_output if self.reviewed_output else self.raw_output

    def __repr__(self) -> str:
        return f"<Result id={self.id} job_id={self.job_id} finalized={self.is_finalized}>"
