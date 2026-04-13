from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import auth_router, document_router, export_router, job_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.redis_client import close_pool
from app.db.session import engine
from app.db.session import close_db
from app.middlewares.error_handler import register_exception_handlers
from app.models import Base

configure_logging()
settings = get_settings()
logger = get_logger(__name__)

app = FastAPI(title="Async Document Processor", version="1.0.0")

# Configure CORS
allowed_origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(document_router, prefix="/api/v1")
app.include_router(job_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

register_exception_handlers(app)


@app.on_event("startup")
async def startup() -> None:
    # Skip database validation on startup to avoid SQLAlchemy sync pool issues with asyncpg
    # Database connections will be validated on first API request requiring a session
    logger.info("Application starting up")


@app.on_event("shutdown")
async def shutdown() -> None:
    await close_db()
    await close_pool()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
