"""
Stores the uploaded document file.

When someone uploads a file, the metadata and location go here.
The actual processing jobs are tracked separately in the Job table.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Document(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "documents"

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)

    # Who uploaded this file (only set if authentication is enabled)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # A document can have multiple jobs (e.g., if you retry processing)
    # But retry creates a new job, not a new document
    jobs: Mapped[list["Job"]] = relationship(  # noqa: F821
        "Job",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="raise",   # always use joinedload() to avoid slow N+1 queries
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename!r}>"
