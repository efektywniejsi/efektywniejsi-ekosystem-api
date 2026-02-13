"""Application-wide exception classes and handlers.

This module provides a consistent exception hierarchy for the application
and registers global exception handlers with FastAPI.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base exception for application errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found error (404)."""

    def __init__(self, message: str = "Zasób nie znaleziony", resource: str | None = None):
        details = {"resource": resource} if resource else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details=details,
        )


class ValidationError(AppError):
    """Validation error (400)."""

    def __init__(self, message: str = "Błąd walidacji", field: str | None = None):
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class ConflictError(AppError):
    """Resource conflict error (409)."""

    def __init__(self, message: str = "Konflikt zasobów", resource: str | None = None):
        details = {"resource": resource} if resource else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details=details,
        )


class UnauthorizedError(AppError):
    """Authentication required error (401)."""

    def __init__(self, message: str = "Wymagane uwierzytelnienie"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
        )


class ForbiddenError(AppError):
    """Access forbidden error (403)."""

    def __init__(self, message: str = "Brak dostępu"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )


class RateLimitError(AppError):
    """Rate limit exceeded error (429)."""

    def __init__(self, message: str = "Przekroczono limit żądań", retry_after: int | None = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


class ExternalServiceError(AppError):
    """External service error (502)."""

    def __init__(self, message: str = "Błąd usługi zewnętrznej", service: str | None = None):
        details = {"service": service} if service else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details,
        )


async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle AppException and return consistent JSON response."""
    logger.error(
        "AppException: %s (code=%s, status=%d)",
        exc.message,
        exc.error_code,
        exc.status_code,
        extra={"details": exc.details},
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details if exc.details else None,
            },
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions with a generic error response."""
    logger.exception("Unhandled exception: %s", str(exc))

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Wystąpił nieoczekiwany błąd",
                "details": None,
            },
        },
    )


def register_exception_handlers(app: FastAPI, *, debug: bool = False) -> None:
    """Register exception handlers with the FastAPI app.

    Call this function in main.py to register all exception handlers.

    Args:
        app: The FastAPI application instance.
        debug: If True, unhandled exceptions propagate with stack traces.
    """
    app.add_exception_handler(AppError, app_exception_handler)  # type: ignore[arg-type]
    if not debug:
        app.add_exception_handler(Exception, unhandled_exception_handler)
