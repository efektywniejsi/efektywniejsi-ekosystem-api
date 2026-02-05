"""Core schema definitions for standardized API responses.

This module provides base schemas for consistent API response format
across the application.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope.

    All API endpoints should return responses wrapped in this format
    for consistency.

    Example success response:
        {
            "success": true,
            "data": { ... },
            "meta": { "total": 100, "page": 1, "limit": 20 }
        }

    Example error response:
        {
            "success": false,
            "error": {
                "code": "NOT_FOUND",
                "message": "Resource not found",
                "details": { "resource": "user" }
            }
        }
    """

    success: bool = True
    data: T | None = None
    error: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    total: int = Field(..., description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    @classmethod
    def from_query(cls, total: int, page: int, limit: int) -> "PaginationMeta":
        """Create pagination meta from query parameters.

        Args:
            total: Total number of items.
            page: Current page number (1-indexed).
            limit: Items per page.

        Returns:
            PaginationMeta instance.
        """
        pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(total=total, page=page, limit=limit, pages=pages)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response with metadata."""

    success: bool = True
    data: list[T]
    meta: PaginationMeta


class ErrorDetail(BaseModel):
    """Error detail structure."""

    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Additional error context")


class ErrorResponse(BaseModel):
    """Standard error response format."""

    success: bool = False
    error: ErrorDetail


def success_response(data: T, meta: dict[str, Any] | None = None) -> ApiResponse[T]:
    """Create a successful API response.

    Args:
        data: The response data.
        meta: Optional metadata.

    Returns:
        ApiResponse with success=True.
    """
    return ApiResponse(success=True, data=data, meta=meta)


def error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> ApiResponse[None]:
    """Create an error API response.

    Args:
        code: Error code.
        message: Error message.
        details: Optional error details.

    Returns:
        ApiResponse with success=False.
    """
    return ApiResponse(
        success=False,
        error={"code": code, "message": message, "details": details},
    )


def paginated_response(
    data: list[T],
    total: int,
    page: int,
    limit: int,
) -> PaginatedResponse[T]:
    """Create a paginated response.

    Args:
        data: List of items for current page.
        total: Total number of items.
        page: Current page number.
        limit: Items per page.

    Returns:
        PaginatedResponse with pagination metadata.
    """
    return PaginatedResponse(
        data=data,
        meta=PaginationMeta.from_query(total, page, limit),
    )
