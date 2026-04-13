"""
Sets up the database connection and sessions.

This creates one connection pool that the whole app uses to talk to the database.
FastAPI routes automatically get a database session to use.
Background tasks can open their own sessions too.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# -----------
# Engine
# -----------
# Use a simple connection pool without automatic recycling
# This is safe for background tasks that may spawn new processes

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.is_development,     # log SQL in dev, silent in prod
    pool_pre_ping=True,               # detect stale connections
    poolclass=NullPool,               # safe for both API and worker processes
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # avoid lazy-load errors after commit
    autoflush=False,
    autocommit=False,
)


# -----
# FastAPI dependency
# -----

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # This provides a database session for each request
    # It automatically saves changes if everything works,
    # or undoes changes if something goes wrong
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ------
# Startup / shutdown helpers
# ------

async def init_db() -> None:
    # Check that we can connect to the database when the app starts
    # If it fails, we won't start the app
    from sqlalchemy import text

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database connection verified")
    except Exception as exc:
        logger.error("database connection failed", extra={"error": str(exc)})
        raise


async def close_db() -> None:
    # Close the database connection when the app shuts down
    await engine.dispose()
    logger.info("database engine disposed")