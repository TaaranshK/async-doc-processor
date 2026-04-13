from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_ENV: Literal["development", "staging", "production"] = "development"

    SECRET_KEY: str = Field(
        "change-me-generate-a-strong-random-secret",
        min_length=32,
        description="JWT signing secret used by auth.",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"
    CORS_ORIGINS_STR: str = "*"

    @computed_field
    @property
    def CORS_ORIGINS(self) -> list[str]:
        if self.CORS_ORIGINS_STR == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS_STR.split(",") if origin.strip()]

    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "docprocessor"
    POSTGRES_USER: str = "docuser"
    POSTGRES_PASSWORD: str = "changeme"
    DATABASE_URL_OVERRIDE: str | None = None
    SYNC_DATABASE_URL_OVERRIDE: str | None = None

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> str:
        if self.SYNC_DATABASE_URL_OVERRIDE:
            return self.SYNC_DATABASE_URL_OVERRIDE
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_URL_OVERRIDE: str | None = None

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_URL_OVERRIDE:
            return self.REDIS_URL_OVERRIDE
        if self.REDIS_PASSWORD:
            return (
                f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}"
                f":{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_MAX_RETRIES: int = 3
    CELERY_RETRY_BACKOFF_BASE: int = 2

    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_PATH: str = "/app/uploads"
    MAX_FILE_SIZE_BYTES: int = 52_428_800
    CHUNKED_WRITE_THRESHOLD_BYTES: int = 10_485_760
    ALLOWED_MIME_TYPES_STR: str = "application/pdf,text/plain,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    @computed_field
    @property
    def ALLOWED_MIME_TYPES(self) -> list[str]:
        return [mime.strip() for mime in self.ALLOWED_MIME_TYPES_STR.split(",") if mime.strip()]

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = ""

    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"
    INTERNAL_API_URL: str = "http://api:8000"

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def celery_retry_delays(self) -> list[int]:
        return [2, 8, 32][: self.CELERY_MAX_RETRIES]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
