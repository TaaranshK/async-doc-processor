from __future__ import annotations

import os
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

TEST_DIR = Path(__file__).resolve().parent
DB_PATH = TEST_DIR / "test_app.db"
UPLOADS_PATH = TEST_DIR / "uploads"

os.environ["DATABASE_URL_OVERRIDE"] = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"
os.environ["SYNC_DATABASE_URL_OVERRIDE"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["REDIS_URL_OVERRIDE"] = "redis://localhost:6379/0"

from app.core.config import settings
from app.db import session as db_session_module
import app.main as app_main_module
from app.models import Base


settings.LOCAL_STORAGE_PATH = str(UPLOADS_PATH)
UPLOADS_PATH.mkdir(parents=True, exist_ok=True)

test_engine = create_async_engine(settings.DATABASE_URL, future=True, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)
db_session_module.engine = test_engine
db_session_module.SessionLocal = TestSessionLocal
app_main_module.engine = test_engine
app = app_main_module.app


@pytest_asyncio.fixture(autouse=True)
async def reset_database():
    if DB_PATH.exists():
        DB_PATH.unlink()
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
