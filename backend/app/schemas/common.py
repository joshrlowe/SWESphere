"""Common schemas for pagination and standard responses."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.pagination import calculate_pages

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination query parameters."""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")

    @property
    def skip(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        """Alias for per_page."""
        return self.per_page


class MessageResponse(BaseModel):
    """Standard message response."""

    message: str
    success: bool = True


class ErrorDetail(BaseModel):
    """Error detail information."""

    loc: list[str] | None = None
    msg: str
    type: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str | list[ErrorDetail]
    success: bool = False


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        per_page: int,
    ) -> "PaginatedResponse[T]":
        """Create a paginated response with computed pages."""
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=calculate_pages(total, per_page),
        )

