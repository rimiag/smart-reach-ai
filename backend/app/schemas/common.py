"""
Common Schemas

Shared Pydantic models used across multiple endpoints.
"""

from typing import Any, Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


# -----------------------------------------------------------------------------
# Response Wrappers
# -----------------------------------------------------------------------------
class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    data: Any = None


class ErrorResponse(BaseModel):
    """Error response structure."""

    error: dict


# -----------------------------------------------------------------------------
# Common Models
# -----------------------------------------------------------------------------
class IDResponse(BaseModel):
    """Response with just an ID."""

    id: int


class BulkActionRequest(BaseModel):
    """Bulk action on multiple items."""

    ids: List[int]


class BulkActionResponse(BaseModel):
    """Response for bulk actions."""

    success_count: int
    failed_count: int
    errors: List[str] = []
