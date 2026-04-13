"""
Import all models here so Alembic's autogenerate can discover them.
"""

from app.models.base import Base
from app.models.document_model import Document
from app.models.job_model import Job, JobStatus
from app.models.result_model import Result
from app.models.user_model import User

__all__ = ["Base", "Document", "Job", "JobStatus", "Result", "User"]
