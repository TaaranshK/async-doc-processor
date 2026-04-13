"""
Provides common things that API routes need, like database sessions and the current user.

Instead of creating a database session in every route,
we define it here once and FastAPI automatically passes it to routes that need it.
"""

from __future__ import annotations

import logging
from typing import Annotated, AsyncGenerator
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.job import Job, JobStatus
from app.models.result import Result
from app.models.user import User

logger = logging.getLogger(__name__)

# -----
# OAuth2 (token-based authentication)
# -----
# This tells FastAPI where users log in to get a token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,  # Let get_current_user decide what to do if token is missing
)

# --------
# Database
# --------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Get a database session for this request
    # Automatically closes the session when done
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


DbSession = Annotated[AsyncSession, Depends(get_db)]

# -----
# Redis
# -----

async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    # Get a Redis connection for this request
    # Used to watch progress updates and send cancellation signals
    client: aioredis.Redis = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True,
    )
    try:
        yield client
    finally:
        await client.aclose()


RedisClient = Annotated[aioredis.Redis, Depends(get_redis)]

# --------
# JWT / Authentication
# ---------------------------------------------------------------------------


class TokenPayload(BaseModel):
    sub: str  # user ID (UUID string)
    exp: int  # UNIX timestamp


async def get_current_user(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    # Check if the user has a valid login token
    # If not, or if the token is old, return an error
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credentials_exc

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValueError):
        logger.warning("JWT decode failed", exc_info=True)
        raise credentials_exc

    user_id: UUID
    try:
        user_id = UUID(token_data.sub)
    except ValueError:
        raise credentials_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exc

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

# ------
# Optional authentication (returns None if not logged in)
# ------

async def get_optional_user(
    db: DbSession,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User | None:
    # Get the logged-in user if they have a token, otherwise return None
    if token is None:
        return None
    try:
        return await get_current_user(db, token)
    except HTTPException:
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]

# ------
# Job existence guard (check if job belongs to user)
# ------

async def get_job(
    job_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> Job:
    # Find a job by ID
    # Make sure it belongs to the logged-in user
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # When auth is disabled (uploaded_by is NULL), skip the ownership check.
    if job.uploaded_by is not None and job.uploaded_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this job",
        )

    return job


JobDep = Annotated[Job, Depends(get_job)]

# --------
# Result guard (check if result exists)
# --------

async def get_job_result(job: JobDep, db: DbSession) -> Result:
    # Get the result for a job
    # If the job is still processing, there's no result yet
    result_row = await db.execute(select(Result).where(Result.job_id == job.id))
    result = result_row.scalar_one_or_none()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No result available yet for job {job.id} (status: {job.status})",
        )

    return result


JobResultDep = Annotated[Result, Depends(get_job_result)]


async def require_finalized_result(result: JobResultDep) -> Result:
    # Make sure the result is finalized before allowing export
    # Results need to be finalized (checked by user) before they can be exported
    if not result.is_finalized:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Result must be finalized before it can be exported",
        )
    return result


FinalizedResultDep = Annotated[Result, Depends(require_finalized_result)]

# ------
# Active job guard (for cancelling jobs)
# ------

async def get_active_job(job: JobDep) -> Job:
    # Check if the job can still be cancelled
    # Can't cancel a job that's already done
    terminal = {JobStatus.completed, JobStatus.failed, JobStatus.cancelled}
    if job.status in terminal:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job {job.id} is already in terminal state '{job.status}'",
        )
    return job


ActiveJobDep = Annotated[Job, Depends(get_active_job)]

# ------
# Failed job guard (for retrying jobs)
# ------

async def get_failed_job(job: JobDep) -> Job:
    # Check if a job failed and can be retried
    if job.status != JobStatus.failed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only failed jobs can be retried (current status: '{job.status}')",
        )

    if job.retry_count >= settings.MAX_JOB_RETRIES:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Job {job.id} has reached the maximum retry limit ({settings.MAX_JOB_RETRIES})",
        )

    return job


FailedJobDep = Annotated[Job, Depends(get_failed_job)]

# ------
# Common query parameters
# ------

class PaginationParams(BaseModel):
    # Standard pagination for list endpoints
    # Lets the user say which page they want and how many items per page

    page: int = Query(default=1, ge=1, description="1-based page number")
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class JobFilterParams(BaseModel):
    """
    Filter / sort parameters for GET /api/v1/jobs.

    Matches the dashboard spec:
      - Free-text search on filename
      - Multi-value status filter
      - Sort by created_at or status
    """

    search: str | None = Query(
        default=None,
        max_length=255,
        description="Free-text search on document filename",
    )
    status: list[JobStatus] | None = Query(
        default=None,
        description="Filter by one or more job statuses",
    )
    sort_by: str = Query(
        default="created_at",
        pattern="^(created_at|status)$",
        description="Sort field: 'created_at' or 'status'",
    )
    sort_order: str = Query(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort direction",
    )


PaginationDep = Annotated[PaginationParams, Depends(PaginationParams)]
JobFilterDep = Annotated[JobFilterParams, Depends(JobFilterParams)]


# ---------------------------------------------------------------------------
# Bulk export query parameters
# ---------------------------------------------------------------------------


class BulkExportParams(BaseModel):
    """
    Query parameters for GET /api/v1/export/bulk.

    'ids' is a comma-separated list of finalized job UUIDs.
    """

    ids: str = Query(
        ...,
        description="Comma-separated list of finalized job UUIDs to export",
    )
    format: str = Query(
        default="json",
        pattern="^(json|csv)$",
        description="Export format: 'json' or 'csv'",
    )

    def parsed_ids(self) -> list[UUID]:
        try:
            return [UUID(raw.strip()) for raw in self.ids.split(",") if raw.strip()]
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid UUID in ids parameter: {exc}",
            ) from exc


BulkExportDep = Annotated[BulkExportParams, Depends(BulkExportParams)]