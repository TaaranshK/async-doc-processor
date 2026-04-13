"""
Document processing pipeline - does all the work to extract information from documents.

The pipeline works in 6 steps:
1. Validate - Check if the file is real and the right type
2. Extract Text - Get all the text from the file (handles PDFs, Word docs, images, etc.)
3. Chunk - Split the text into smaller pieces
4. Analyse - Use AI to find important info like names, summaries, key details
5. Persist - Save the results to the database
6. Finalise - Mark the job as complete

Each step sends progress updates and checks if the user wants to cancel.
If something goes wrong, the error is saved and the job is marked as failed.
"""

from __future__ import annotations

import io
import json
import mimetypes
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from celery.utils.log import get_task_logger

from app.core.config import get_settings
from app.core.redis_client import (
    clear_cancellation_flag,
    is_cancelled,
    publish_progress,
)
from app.db.session import async_session_factory
from app.models.job import Job, JobStatus
from app.models.result import Result
from app.schemas.progress import ProgressEvent
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

if TYPE_CHECKING:
    from celery import Task

logger = get_task_logger(__name__)

settings = get_settings()

# --------
# Exceptions
# --------


class PipelineError(Exception):
    # Something went wrong during processing


class PipelineStageError(PipelineError):
    # A specific processing step failed
    # It says which step failed, what went wrong, and whether we can try again

    def __init__(self, stage: str, message: str, *, recoverable: bool = False) -> None:
        # Parameters:
        # - stage: which step failed (like "extract_text")
        # - message: what the error is
        # - recoverable: can we retry this, or is it permanently broken?
        super().__init__(message)
        self.stage = stage
        self.message = message
        self.recoverable = recoverable


class PipelineCancelledError(PipelineError):
    # The user asked to cancel the job while it was processing


# ------------------
# Stage result carrier
# ------------------


@dataclass
class StageResult:
    """
    Typed carrier passed from one stage to the next.

    Attributes
    ----------
    job_id:
        UUID of the job being processed.
    document_id:
        UUID of the source document.
    storage_path:
        Absolute path (local) or S3 key to the uploaded file.
    file_type:
        MIME type of the uploaded file (e.g. ``"application/pdf"``).
    raw_text:
        Plain text extracted by the ``extract_text`` stage.
    chunks:
        List of text chunks produced by the ``chunk`` stage.
    extracted_fields:
        Structured fields produced by the ``analyse`` stage.
    summary:
        Short summary produced by the ``analyse`` stage.
    entities:
        Named entities [{text, label, start, end}] from ``analyse``.
    word_count:
        Total word count of ``raw_text`` (set after extraction).
    page_count:
        Number of pages (PDFs only; 1 for all other types).
    """

    job_id: uuid.UUID
    document_id: uuid.UUID
    storage_path: str
    file_type: str
    raw_text: str = ""
    chunks: list[str] = field(default_factory=list)
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    entities: list[dict[str, Any]] = field(default_factory=list)
    word_count: int = 0
    page_count: int = 1


# ---------------------------------------------------------------------------
# Progress helper
# ---------------------------------------------------------------------------

# Canonical stage weights (must sum to 100).
_STAGE_PROGRESS: dict[str, tuple[int, int]] = {
    "validate":     (0,   10),
    "extract_text": (10,  35),
    "chunk":        (35,  50),
    "analyse":      (50,  85),
    "persist":      (85,  95),
    "finalise":     (95, 100),
}


async def _emit(
    job_id: uuid.UUID,
    stage: str,
    pct: int,
    message: str,
    status: str = "processing",
    error: str | None = None,
) -> None:
    # Send a progress update to the user and save it to the database
    # 1. Redis Pub/Sub — fast path for live SSE consumers.
    event = ProgressEvent(
        job_id=str(job_id),
        stage=stage,
        progress_pct=pct,
        message=message,
        status=status,
        error=error,
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
    )
    await publish_progress(str(job_id), event.model_dump())

    # 2. PostgreSQL — so GET /jobs/{id} returns current progress.
    async with async_session_factory() as session:
        await session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                current_stage=stage,
                progress_pct=pct,
                updated_at=datetime.now(tz=timezone.utc),
            )
        )
        await session.commit()


async def _check_cancelled(job_id: uuid.UUID) -> None:
    # Check if the user asked to cancel this job
    if await is_cancelled(str(job_id)):
        raise PipelineCancelledError(f"Job {job_id} was cancelled")


# -----
# Stage 1 - validate
# -----


async def _stage_validate(ctx: StageResult) -> StageResult:
    # Check that the uploaded file exists and is a valid type
    await _check_cancelled(ctx.job_id)
    start, _ = _STAGE_PROGRESS["validate"]
    await _emit(ctx.job_id, "validate", start, "Validating file")

    path = Path(ctx.storage_path)

    # --- Local storage path ---
    if not ctx.storage_path.startswith("s3://"):
        if not path.exists():
            raise PipelineStageError(
                "validate",
                f"File not found on disk: {ctx.storage_path}",
                recoverable=False,
            )
        if path.stat().st_size == 0:
            raise PipelineStageError(
                "validate",
                "Uploaded file is empty",
                recoverable=False,
            )

    # --- S3 path ---
    else:
        try:
            from app.storage.s3 import head_object  # lazy import
            await head_object(ctx.storage_path)
        except Exception as exc:
            raise PipelineStageError(
                "validate",
                f"Cannot access S3 object: {exc}",
                recoverable=True,   # transient S3 errors are retryable
            ) from exc

    # --- MIME type check ---
    allowed = set(settings.ALLOWED_MIME_TYPES)
    if ctx.file_type not in allowed:
        raise PipelineStageError(
            "validate",
            f"MIME type '{ctx.file_type}' is not in ALLOWED_MIME_TYPES",
            recoverable=False,
        )

    _, end = _STAGE_PROGRESS["validate"]
    await _emit(ctx.job_id, "validate", end, "File validated successfully")
    logger.info("validate OK | job=%s | path=%s", ctx.job_id, ctx.storage_path)
    return ctx


# ---------------------------------------------------------------------------
# Stage 2 — extract_text
# ---------------------------------------------------------------------------


async def _read_file_bytes(storage_path: str) -> bytes:
    # Read the file bytes from either local disk or S3
    if storage_path.startswith("s3://"):
        from app.storage.s3 import download_bytes  # lazy import
        return await download_bytes(storage_path)
    return Path(storage_path).read_bytes()


def _extract_pdf(data: bytes) -> tuple[str, int]:
    # Extract text from a PDF file
    import pdfplumber  # type: ignore[import]

    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)

    return "\n\n".join(pages), page_count


def _extract_docx(data: bytes) -> str:
    # Extract text from a Word document
    import docx  # type: ignore[import]

    doc = docx.Document(io.BytesIO(data))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_image_ocr(data: bytes) -> str:
    # Extract text from an image using OCR
    import pytesseract  # type: ignore[import]
    from PIL import Image  # type: ignore[import]

    image = Image.open(io.BytesIO(data))
    return pytesseract.image_to_string(image, lang="eng")


async def _stage_extract_text(ctx: StageResult) -> StageResult:
    # Extract all the text from the uploaded file
    # Handle PDFs, Word docs, images, and plain text
    await _check_cancelled(ctx.job_id)
    start, end = _STAGE_PROGRESS["extract_text"]
    await _emit(ctx.job_id, "extract_text", start, "Reading file")

    data = await _read_file_bytes(ctx.storage_path)

    await _emit(ctx.job_id, "extract_text", start + 5, "Extracting text")

    mime = ctx.file_type
    raw_text = ""
    page_count = 1

    try:
        if mime == "application/pdf":
            raw_text, page_count = _extract_pdf(data)

        elif mime in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            raw_text = _extract_docx(data)

        elif mime == "text/plain":
            raw_text = data.decode("utf-8", errors="replace")

        elif mime.startswith("image/"):
            raw_text = _extract_image_ocr(data)

        else:
            raise PipelineStageError(
                "extract_text",
                f"No extractor available for MIME type: {mime}",
                recoverable=False,
            )
    except PipelineStageError:
        raise
    except Exception as exc:
        raise PipelineStageError(
            "extract_text",
            f"Text extraction failed: {exc}",
            recoverable=False,
        ) from exc

    # Normalise whitespace.
    raw_text = re.sub(r"\n{3,}", "\n\n", raw_text).strip()

    if not raw_text:
        raise PipelineStageError(
            "extract_text",
            "No text could be extracted from the document",
            recoverable=False,
        )

    ctx.raw_text = raw_text
    ctx.page_count = page_count
    ctx.word_count = len(raw_text.split())

    await _emit(
        ctx.job_id,
        "extract_text",
        end,
        f"Extracted {ctx.word_count:,} words from {page_count} page(s)",
    )
    logger.info(
        "extract_text OK | job=%s | words=%d | pages=%d",
        ctx.job_id, ctx.word_count, ctx.page_count,
    )
    return ctx


# ---------------------------------------------------------------------------
# Stage 3 — chunk
# ---------------------------------------------------------------------------

_CHUNK_SIZE = 1_000      # target words per chunk
_CHUNK_OVERLAP = 100     # words of overlap between consecutive chunks


def _split_into_chunks(text: str, size: int, overlap: int) -> list[str]:
    """
    Split ``text`` into overlapping word-level chunks.

    Parameters
    ----------
    text:
        Full document text.
    size:
        Target number of words per chunk.
    overlap:
        Number of words from the end of chunk N to repeat at the start
        of chunk N+1.  Provides context continuity for NLP models.

    Returns
    -------
    list[str]
        Ordered list of text chunks.  The last chunk may be shorter than
        ``size``.
    """
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += size - overlap

    return chunks


async def _stage_chunk(ctx: StageResult) -> StageResult:
    """
    Split extracted text into overlapping word-level chunks.

    Short documents (< ``_CHUNK_SIZE`` words) are kept as a single chunk.
    Chunk size and overlap are constants at the top of this module and
    can be promoted to settings later.
    """
    await _check_cancelled(ctx.job_id)
    start, end = _STAGE_PROGRESS["chunk"]
    await _emit(ctx.job_id, "chunk", start, "Splitting document into chunks")

    ctx.chunks = _split_into_chunks(ctx.raw_text, _CHUNK_SIZE, _CHUNK_OVERLAP)

    await _emit(
        ctx.job_id,
        "chunk",
        end,
        f"Split into {len(ctx.chunks)} chunk(s)",
    )
    logger.info("chunk OK | job=%s | chunks=%d", ctx.job_id, len(ctx.chunks))
    return ctx


# ---------------------------------------------------------------------------
# Stage 4 — analyse
# ---------------------------------------------------------------------------


def _extract_entities(text: str) -> list[dict[str, Any]]:
    # Find names, places, and other named things in the text using AI
    try:
        import spacy  # type: ignore[import]
        nlp = spacy.load("en_core_web_sm")
        # Disable unused pipes for speed.
        with nlp.select_pipes(enable=["ner"]):
            doc = nlp(text[:100_000])  # cap at 100k chars to avoid OOM
        return [
            {"text": ent.text, "label": ent.label_, "start": ent.start_char, "end": ent.end_char}
            for ent in doc.ents
        ]
    except Exception:  # noqa: BLE001
        logger.warning("spaCy entity extraction failed — returning empty list", exc_info=True)
        return []


def _build_summary(text: str, max_sentences: int = 5) -> str:
    # Create a simple summary from the first few sentences
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:max_sentences])


def _extract_kv_fields(text: str) -> dict[str, Any]:
    # Find important info like dates, emails, and phone numbers using patterns
    date_pattern = re.compile(
        r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}"
        r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
        re.IGNORECASE,
    )
    email_pattern = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
    phone_pattern = re.compile(
        r"(\+?1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}"
    )
    money_pattern = re.compile(
        r"[\$£€]\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?"
        r"|\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s?(?:USD|GBP|EUR|dollars?|pounds?|euros?)",
        re.IGNORECASE,
    )

    return {
        "dates": list({m.group() for m in date_pattern.finditer(text)}),
        "emails": list({m.group() for m in email_pattern.finditer(text)}),
        "phone_numbers": list({m.group() for m in phone_pattern.finditer(text)}),
        "monetary_amounts": list({m.group() for m in money_pattern.finditer(text)}),
    }


async def _stage_analyse(ctx: StageResult) -> StageResult:
    """
    Run NLP analysis on the extracted text: entities, summary, key-value fields.

    All heavy computation runs in the default executor (ThreadPoolExecutor)
    via ``asyncio.to_thread`` so the event loop stays responsive during
    CPU-bound spaCy / regex work.
    """
    import asyncio

    await _check_cancelled(ctx.job_id)
    start, end = _STAGE_PROGRESS["analyse"]
    await _emit(ctx.job_id, "analyse", start, "Analysing document")

    # Use the full text for analysis (not chunks — chunking is for retrieval).
    text = ctx.raw_text

    await _emit(ctx.job_id, "analyse", start + 10, "Extracting entities")
    ctx.entities = await asyncio.to_thread(_extract_entities, text)

    await _emit(ctx.job_id, "analyse", start + 20, "Building summary")
    ctx.summary = await asyncio.to_thread(_build_summary, text)

    await _emit(ctx.job_id, "analyse", start + 30, "Extracting key fields")
    ctx.extracted_fields = await asyncio.to_thread(_extract_kv_fields, text)

    # Annotate with metadata fields.
    ctx.extracted_fields.update(
        {
            "word_count": ctx.word_count,
            "page_count": ctx.page_count,
            "chunk_count": len(ctx.chunks),
            "entity_count": len(ctx.entities),
            "summary": ctx.summary,
        }
    )

    await _emit(
        ctx.job_id,
        "analyse",
        end,
        f"Analysis complete — {len(ctx.entities)} entit{'y' if len(ctx.entities)==1 else 'ies'} found",
    )
    logger.info(
        "analyse OK | job=%s | entities=%d | fields=%d",
        ctx.job_id, len(ctx.entities), len(ctx.extracted_fields),
    )
    return ctx


# ---------------------------------------------------------------------------
# Stage 5 — persist
# ---------------------------------------------------------------------------


async def _stage_persist(ctx: StageResult) -> StageResult:
    """
    Write (or upsert) the :class:`~app.models.result.Result` row to PostgreSQL.

    The ``raw_output`` JSONB column receives the full structured payload.
    If a Result row already exists for this job (idempotent re-run), it
    is updated rather than duplicated.
    """
    await _check_cancelled(ctx.job_id)
    start, end = _STAGE_PROGRESS["persist"]
    await _emit(ctx.job_id, "persist", start, "Saving results to database")

    payload: dict[str, Any] = {
        "raw_text": ctx.raw_text,
        "chunks": ctx.chunks,
        "entities": ctx.entities,
        "summary": ctx.summary,
        "extracted_fields": ctx.extracted_fields,
        "word_count": ctx.word_count,
        "page_count": ctx.page_count,
        "processed_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    async with async_session_factory() as session:
        # Check for existing result (idempotent upsert).
        existing = await session.scalar(
            select(Result).where(Result.job_id == ctx.job_id)
        )

        if existing is not None:
            existing.raw_output = payload
            existing.updated_at = datetime.now(tz=timezone.utc)
            logger.info("persist: updating existing Result for job %s", ctx.job_id)
        else:
            session.add(
                Result(
                    job_id=ctx.job_id,
                    raw_output=payload,
                )
            )
            logger.info("persist: inserting new Result for job %s", ctx.job_id)

        await session.commit()

    await _emit(ctx.job_id, "persist", end, "Results saved")
    return ctx


# ---------------------------------------------------------------------------
# Stage 6 — finalise
# ---------------------------------------------------------------------------


async def _stage_finalise(ctx: StageResult) -> StageResult:
    """
    Mark the job COMPLETED in PostgreSQL and publish a terminal progress event.

    The terminal event causes :func:`~app.core.redis_client.subscribe_progress`
    to close the async generator, which in turn closes the SSE response.
    """
    start, end = _STAGE_PROGRESS["finalise"]
    await _emit(ctx.job_id, "finalise", start, "Finalising job")

    async with async_session_factory() as session:
        await session.execute(
            update(Job)
            .where(Job.id == ctx.job_id)
            .values(
                status=JobStatus.COMPLETED,
                current_stage="completed",
                progress_pct=100,
                updated_at=datetime.now(tz=timezone.utc),
            )
        )
        await session.commit()

    # Terminal event — SSE subscriber closes on "completed" status.
    await _emit(
        ctx.job_id,
        "completed",
        end,
        "Document processing complete",
        status="completed",
    )
    logger.info("finalise OK | job=%s | COMPLETED", ctx.job_id)
    return ctx


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

# Ordered list of (stage_name, stage_coroutine_function).
_STAGES = [
    ("validate",     _stage_validate),
    ("extract_text", _stage_extract_text),
    ("chunk",        _stage_chunk),
    ("analyse",      _stage_analyse),
    ("persist",      _stage_persist),
    ("finalise",     _stage_finalise),
]


async def run_pipeline(job_id: str, task: "Task") -> dict[str, Any]:
    """
    Execute all six pipeline stages in order for the given job.

    This is the sole entry-point called by
    :func:`~app.workers.tasks.process_document`.  It:

    1. Loads the Job + Document from the DB (single JOIN query).
    2. Builds a :class:`StageResult` context object.
    3. Runs each stage in sequence, passing the mutated context forward.
    4. Handles :exc:`PipelineCancelledError` and :exc:`PipelineStageError`
       gracefully, updating the DB and publishing terminal events.

    Parameters
    ----------
    job_id:
        String UUID of the job.
    task:
        The bound Celery :class:`~celery.Task` instance (used for
        future ``task.update_state()`` calls if needed).

    Returns
    -------
    dict
        ``{"status": "completed"|"cancelled"|"failed", "job_id": job_id}``
    """
    _job_id = uuid.UUID(job_id)

    # ------------------------------------------------------------------
    # Load Job + Document in a single JOIN (no N+1).
    # ------------------------------------------------------------------
    async with async_session_factory() as session:
        row = await session.scalar(
            select(Job)
            .where(Job.id == _job_id)
            .options(joinedload(Job.document))
        )

    if row is None or row.document is None:
        logger.error("run_pipeline: job or document not found | job_id=%s", job_id)
        return {"status": "failed", "job_id": job_id, "error": "job_or_document_not_found"}

    ctx = StageResult(
        job_id=_job_id,
        document_id=row.document.id,
        storage_path=row.document.storage_path,
        file_type=row.document.file_type,
    )

    # ------------------------------------------------------------------
    # Execute stages.
    # ------------------------------------------------------------------
    for stage_name, stage_fn in _STAGES:
        try:
            ctx = await stage_fn(ctx)

        except PipelineCancelledError:
            logger.info("Pipeline cancelled at stage '%s' | job=%s", stage_name, job_id)
            async with async_session_factory() as session:
                await session.execute(
                    update(Job)
                    .where(Job.id == _job_id)
                    .values(
                        status=JobStatus.CANCELLED,
                        current_stage="cancelled",
                        progress_pct=_STAGE_PROGRESS[stage_name][0],
                        updated_at=datetime.now(tz=timezone.utc),
                    )
                )
                await session.commit()
            await _emit(
                _job_id,
                "cancelled",
                _STAGE_PROGRESS[stage_name][0],
                "Job was cancelled",
                status="cancelled",
            )
            await clear_cancellation_flag(job_id)
            return {"status": "cancelled", "job_id": job_id}

        except PipelineStageError as exc:
            logger.error(
                "Pipeline stage '%s' failed | job=%s | recoverable=%s | msg=%s",
                exc.stage, job_id, exc.recoverable, exc.message,
            )
            async with async_session_factory() as session:
                await session.execute(
                    update(Job)
                    .where(Job.id == _job_id)
                    .values(
                        status=JobStatus.FAILED,
                        current_stage=exc.stage,
                        error_message=exc.message,
                        progress_pct=_STAGE_PROGRESS.get(exc.stage, ("", 0))[0],
                        updated_at=datetime.now(tz=timezone.utc),
                    )
                )
                await session.commit()
            await _emit(
                _job_id,
                exc.stage,
                _STAGE_PROGRESS.get(exc.stage, ("", 0))[0],
                f"Stage '{exc.stage}' failed",
                status="failed",
                error=exc.message,
            )
            return {"status": "failed", "job_id": job_id, "error": exc.message}

        except Exception as exc:
            # Catch-all for unexpected errors inside a stage.
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.exception(
                "Unexpected error in stage '%s' | job=%s", stage_name, job_id
            )
            async with async_session_factory() as session:
                await session.execute(
                    update(Job)
                    .where(Job.id == _job_id)
                    .values(
                        status=JobStatus.FAILED,
                        current_stage=stage_name,
                        error_message=error_msg,
                        progress_pct=_STAGE_PROGRESS[stage_name][0],
                        updated_at=datetime.now(tz=timezone.utc),
                    )
                )
                await session.commit()
            await _emit(
                _job_id,
                stage_name,
                _STAGE_PROGRESS[stage_name][0],
                "An unexpected error occurred",
                status="failed",
                error=error_msg,
            )
            raise  # Re-raise so process_document's outer handler fires.

    return {"status": "completed", "job_id": job_id}