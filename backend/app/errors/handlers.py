"""FastAPI exception handlers rendering problem+json."""
from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.errors.exceptions import RoverError
from app.observability.logging_config import get_logger, log_event

_logger = get_logger("errors")


async def rover_error_handler(request: Request, exc: RoverError) -> JSONResponse:
    """Render a RoverError as application/problem+json."""
    log_event(
        _logger,
        logging.WARNING,
        "handled_error",
        code=exc.code,
        status=exc.status_code,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_problem(instance=str(request.url.path)),
        media_type="application/problem+json",
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render an unexpected exception as a generic 500 problem document."""
    log_event(
        _logger,
        logging.ERROR,
        "unhandled_error",
        error=type(exc).__name__,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "type": "https://errors.crowdcompass/internal_error",
            "title": "Internal Server Error",
            "status": 500,
            "code": "internal_error",
            "detail": "An unexpected error occurred.",
            "instance": str(request.url.path),
        },
        media_type="application/problem+json",
    )
