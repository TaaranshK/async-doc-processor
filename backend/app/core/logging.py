"""
Sets up logging for the app.

It logs messages in a human-readable format during development,
and as JSON format in production (for services like Datadog).
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from app.core.config import settings

# Fields that exist on every LogRecord — we skip these when copying extras
_BUILTIN_FIELDS: frozenset[str] = frozenset(logging.LogRecord(
    "", 0, "", 0, "", (), None
).__dict__.keys()) | {"message", "asctime"}


class _JsonFormatter(logging.Formatter):
    # Formats log messages as JSON so they're easier to search in production

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()

        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.message,
        }

        # Copy any extra={...} fields the caller passed
        for key, value in record.__dict__.items():
            if key not in _BUILTIN_FIELDS:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str)


class _TextFormatter(logging.Formatter):
    """Colourised formatter for local development."""

    _COLOURS = {
        "DEBUG":    "\033[36m",   # cyan
        "INFO":     "\033[32m",   # green
        "WARNING":  "\033[33m",   # yellow
        "ERROR":    "\033[31m",   # red
        "CRITICAL": "\033[35m",   # magenta
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        colour = self._COLOURS.get(record.levelname, "")
        prefix = (
            f"{colour}{record.levelname:<8}{self._RESET} "
            f"\033[2m{record.name}\033[0m"
        )
        msg = record.getMessage()

        # Append any extra fields inline
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in _BUILTIN_FIELDS and k not in {"message", "asctime"}
        }
        if extras:
            msg += "  " + "  ".join(f"{k}={v}" for k, v in extras.items())

        output = f"{prefix}  {msg}"

        if record.exc_info:
            output += "\n" + self.formatException(record.exc_info)

        return output


def configure_logging() -> None:
    """
    Set up the root logger once at application startup.

    Call this in app.main before anything else logs.
    Subsequent calls are idempotent (handlers are only added once).
    """
    root = logging.getLogger()

    if root.handlers:
        return  # already configured

    handler = logging.StreamHandler(sys.stdout)

    if settings.LOG_FORMAT == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(_TextFormatter())

    root.addHandler(handler)
    root.setLevel(settings.LOG_LEVEL)

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Always use this instead of logging.getLogger() directly so that
    configure_logging() is guaranteed to have run first.
    """
    configure_logging()
    return logging.getLogger(name)