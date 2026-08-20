"""Centralized error handling for the FastAPI application.

Catches unhandled exceptions, logs the full traceback server-side,
and returns sanitized error messages to the frontend (no stack traces,
no file paths, no internal state).
"""

import traceback

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger("errors")

# Patterns to sanitize from error messages
_SANITIZE_PATTERNS = [
    ("/app/", ""),
    ("/tmp/terramorph-", "[workdir]/terramorph-"),
    ("File \"/", "File \""),
]


def _sanitize_message(message: str) -> str:
    """Remove internal paths and sensitive info from error messages."""
    for pattern, replacement in _SANITIZE_PATTERNS:
        message = message.replace(pattern, replacement)
    return message


def register_error_handlers(app) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTPExceptions with consistent format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle Starlette HTTPExceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "status_code": exc.status_code,
                "detail": str(exc.detail),
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle validation-type errors."""
        logger.warning(f"ValueError on {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "status_code": 400,
                "detail": _sanitize_message(str(exc)),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all for unhandled exceptions.

        Logs the full traceback server-side but returns a generic message to the client.
        """
        # Log full details server-side
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}: {exc}\n"
            f"{traceback.format_exc()}"
        )

        # Return sanitized response to client
        # Include the exception type and a cleaned message for debugging
        safe_message = _sanitize_message(str(exc))

        # Truncate very long error messages
        if len(safe_message) > 500:
            safe_message = safe_message[:500] + "..."

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "status_code": 500,
                "detail": f"Internal server error: {safe_message}" if safe_message else "An unexpected error occurred. Check server logs for details.",
            },
        )
