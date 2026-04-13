"""
This model tracks one job - basically a single request to process a document.

When someone uploads a document, a new Job is created.
It tracks the status, progress, and any errors.
If a job fails, it can be retried, which creates a new attempt.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as PgEnum
from sqlalchemy import ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class JobStatus(str, enum.Enum):
    # All the different states a job can be in

    QUEUED     = "queued"        # Waiting to be processed
    PROCESSING = "processing"    # Currently being worked on
    COMPLETED  = "completed"     # Done successfully
    FAILED     = "failed"         # Something went wrong
    CANCELLED  = "cancelled"      # User stopped it


class Job(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "jobs"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[JobStatus] = mapped_column(
        PgEnum(JobStatus, name="jobstatus", create_type=True),
        nullable=False,
        default=JobStatus.QUEUED,
        index=True,
    )

    # Celery task ID - the ID of the background task that's running this job
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, unique=True
    )

    # What step we're currently on (like "extract_text" or "analyse")
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)

    progress_pct: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # If something went wrong, the error message goes here
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # How many times we've tried to process this job
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # Relationships - Link to other database tables
    document: Mapped["Document"] = relationship(  # noqa: F821
        "Document",
        back_populates="jobs",
        lazy="raise",
    )

    # The result (only if processing succeeded)
    result: Mapped["Result | None"] = relationship(  # noqa: F821
        "Result",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="raise",
    )

    @property
    def is_terminal(self) -> bool:
        # Check if the job is in a final state (can't change anymore)
        return self.status in {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }

    def __repr__(self) -> str:
        return f"<Job id={self.id} status={self.status.value}>"