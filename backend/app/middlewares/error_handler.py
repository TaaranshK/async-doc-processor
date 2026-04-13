from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services import (
    DocumentUploadError,
    ExportNotReadyError,
    FileTooLargeError,
    InvalidStatusTransitionError,
    JobNotCompletedError,
    JobNotFoundError,
    ResultAlreadyFinalizedError,
    ResultNotFoundError,
    UnsupportedFileTypeError,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(FileTooLargeError)
    async def _file_too_large(_: Request, exc: FileTooLargeError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": str(exc)},
        )

    @app.exception_handler(UnsupportedFileTypeError)
    async def _unsupported_type(_: Request, exc: UnsupportedFileTypeError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, content={"detail": str(exc)})

    @app.exception_handler(DocumentUploadError)
    async def _upload_error(_: Request, exc: DocumentUploadError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    @app.exception_handler(JobNotFoundError)
    async def _job_not_found(_: Request, exc: JobNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(ResultNotFoundError)
    async def _result_not_found(_: Request, exc: ResultNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(ResultAlreadyFinalizedError)
    async def _result_finalized(_: Request, exc: ResultAlreadyFinalizedError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

    @app.exception_handler(JobNotCompletedError)
    async def _job_not_completed(_: Request, exc: JobNotCompletedError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

    @app.exception_handler(InvalidStatusTransitionError)
    async def _invalid_status(_: Request, exc: InvalidStatusTransitionError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

    @app.exception_handler(ExportNotReadyError)
    async def _export_not_ready(_: Request, exc: ExportNotReadyError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})
