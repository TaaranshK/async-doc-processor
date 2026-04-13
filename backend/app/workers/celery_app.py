"""
Sets up Celery for background task processing.

Celery connects to Redis to get jobs to process.
This file creates the Celery app and configures it.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import Celery
from celery.signals import (
    after_setup_logger,
    after_setup_task_logger,
    worker_init,
    worker_shutdown,
)
from kombu import Exchange, Queue

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)

# ------
# Queue setup (different queues for different task types)
# ------

# Normal routing - sends tasks to the right queue
_DEFAULT_EXCHANGE = Exchange("default", type="direct")

#: For high-priority tasks that need to run first
_HIGH_PRIORITY_EXCHANGE = Exchange("high_priority", type="direct")

# Different queues for different types of tasks
TASK_QUEUES: tuple[Queue, ...] = (
    Queue(
        "default",
        exchange=_DEFAULT_EXCHANGE,
        routing_key="default",
    ),
    Queue(
        "documents",
        exchange=_DEFAULT_EXCHANGE,
        routing_key="documents",
    ),
    Queue(
        "high_priority",
        exchange=_HIGH_PRIORITY_EXCHANGE,
        routing_key="high_priority",
    ),
)

# Map specific tasks to specific queues
TASK_ROUTES: dict[str, dict[str, str]] = {
    "app.workers.tasks.process_document": {"queue": "documents"},
    "app.workers.tasks.cancel_document": {"queue": "high_priority"},
}


# -------
# Factory
# -------


def _build_celery_app() -> Celery:
    # Create and set up the Celery app with all the right settings
    settings = get_settings()

    app = Celery(
        "async_doc_processor",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        # Only load tasks from the workers module, not the whole package
        include=["app.workers.tasks"],
    )

    # -----
    # Broker settings (connection to Redis)
    # -----
    app.conf.broker_transport_options = {
        # How long to wait before giving up on a long task
        # 6 hours is enough for big documents
        "visibility_timeout": 6 * 60 * 60,
        # Keep connection alive for long tasks
        "socket_keepalive": True,
        "retry_on_timeout": True,
        "max_connections": 20,
    }

    # -------
    # Where to store results (also using Redis)
    # -------
    app.conf.result_backend_transport_options = {
        "retry_policy": {
            "max_retries": 5,
            "interval_start": 0.2,
            "interval_step": 0.5,
            "interval_max": 3.0,
        }
    }
    # Keep task results for 24 hours, then delete them
    # The real job state is stored in the database anyway
    app.conf.result_expires = 60 * 60 * 24

    # -----
    # Serialization (how to format messages)
    # -----
    # Use JSON format so everything is compatible
    app.conf.task_serializer = "json"
    app.conf.result_serializer = "json"
    app.conf.accept_content = ["json"]
    app.conf.event_serializer = "json"

    # -------
    # Task execution settings
    # -------
    # Only mark a task as done AFTER it finishes
    # If a worker crashes, the task will be re-run
    app.conf.task_acks_late = True

    # Reject tasks that crash, so they go to dead-letter queue
    # instead of getting stuck in a retry loop
    app.conf.task_reject_on_worker_lost = True

    # Only run one task per worker at a time
    # Document processing is heavy, so we don't want multiple tasks
    app.conf.worker_prefetch_multiplier = 1

    # Restart each worker after 200 tasks to prevent memory leaks
    app.conf.worker_max_tasks_per_child = 200

    # Time limits - soft means graceful shutdown, hard means force kill
    app.conf.task_soft_time_limit = 5 * 60   # warn after 5 minutes
    app.conf.task_time_limit = 10 * 60       # kill after 10 minutes

    # -----
    # Retry settings (if a task fails, try again)
    # -----
    app.conf.task_default_retry_delay = 5
    app.conf.task_max_retries = 3

    # -----
    # Queue configuration (where tasks go)
    # -----
    app.conf.task_queues = TASK_QUEUES
    app.conf.task_routes = TASK_ROUTES
    app.conf.task_default_queue = "default"
    app.conf.task_default_exchange = "default"
    app.conf.task_default_routing_key = "default"

    # -------
    # Timezone
    # -------
    app.conf.timezone = "UTC"
    app.conf.enable_utc = True

    # ---------
    # Scheduled tasks (run periodically)
    # ---------
    # Check for stuck jobs every 10 minutes
    app.conf.beat_schedule = {
        "reap-orphaned-jobs": {
            "task": "app.workers.tasks.reap_orphaned_jobs",
            "schedule": 60 * 10,  # every 10 minutes
            "options": {"queue": "high_priority"},
        },
    }

    # -----
    # Monitoring
    # Emit task events so Flower / custom monitors can track progress.
    app.conf.worker_send_task_events = True
    app.conf.task_send_sent_event = True

    return app


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

celery_app: Celery = _build_celery_app()
"""
The singleton Celery application.

Import this object in tasks, API routers (for `.apply_async`), and tests.

Example::

    from app.workers.celery_app import celery_app

    celery_app.send_task("app.workers.tasks.process_document", args=[job_id])
"""


def get_celery_app() -> Celery:
    """
    Return the singleton :data:`celery_app`.

    Provided as a callable so test fixtures can monkey-patch or override
    the app without replacing the module-level name directly.

    Returns
    -------
    Celery
        The configured Celery application singleton.
    """
    return celery_app


# ---------------------------------------------------------------------------
# Celery signal handlers
# ---------------------------------------------------------------------------


@after_setup_logger.connect
def _configure_celery_logger(
    logger: logging.Logger,  # noqa: F811 — shadows module logger intentionally
    *args: Any,
    **kwargs: Any,
) -> None:
    """
    Replace Celery's default logging setup with our structured formatter.

    Celery fires this signal before any task runs, so the formatter is
    guaranteed to be in place for all worker output.
    """
    configure_logging()


@after_setup_task_logger.connect
def _configure_task_logger(
    logger: logging.Logger,  # noqa: F811
    *args: Any,
    **kwargs: Any,
) -> None:
    """Ensure task-scoped loggers also use our formatter."""
    configure_logging()


@worker_init.connect
def _on_worker_init(**kwargs: Any) -> None:
    """
    Hook called once per worker *process* at startup.

    Use this to warm up connections or run sanity checks before the first
    task is dequeued.  Heavy initialisation (e.g. ML model loading) belongs
    here so it happens once per process, not once per task.
    """
    _log = get_logger(__name__)
    _log.info("Celery worker process initialising")
    # DB engine and Redis pool are created lazily on first use;
    # no explicit warm-up needed here.


@worker_shutdown.connect
def _on_worker_shutdown(**kwargs: Any) -> None:
    """
    Hook called once per worker *process* at shutdown.

    Gives in-flight async resources (e.g. aioredis connections) a chance
    to close cleanly before the process exits.
    """
    import asyncio

    from app.core.redis_client import get_pool
    from app.db.session import close_db

    _log = get_logger(__name__)
    _log.info("Celery worker process shutting down — closing connections")

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(close_db())
        pool = loop.run_until_complete(get_pool())
        loop.run_until_complete(pool.aclose())
    except Exception:  # noqa: BLE001
        _log.warning("Error during worker shutdown cleanup", exc_info=True)
    finally:
        loop.close()