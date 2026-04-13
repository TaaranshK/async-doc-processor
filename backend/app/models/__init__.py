"""
Import all models here so Alembic's autogenerate can discover them.
"""

from app.models.base import Base
from app.models.document import Document
from app.models.job import Job, JobStatus
from app.models.result import Result
from app.models.user import User

__all__ = ["Base", "Document", "Job", "JobStatus", "Result", "User"]