"""
Pagination utilities.

Provides consistent pagination handling across all services and API endpoints.
Consolidates pagination logic to avoid duplication and ensure consistent behavior.
"""

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


# =============================================================================
# Pagination Calculations
# =============================================================================


def calculate_skip(page: int, per_page: int) -> int:
    """
    Calculate database offset from page number.
    
    Args:
        page: 1-indexed page number
        per_page: Items per page
        
    Returns:
        Number of items to skip (offset)
    """
    return (page - 1) * per_page


def calculate_pages(total: int, per_page: int) -> int:
    """
    Calculate total number of pages.
    
    Args:
        total: Total number of items
        per_page: Items per page
        
    Returns:
        Total number of pages
    """
    if per_page <= 0:
        return 0
    return (total + per_page - 1) // per_page


def has_next_page(page: int, per_page: int, total: int) -> bool:
    """
    Check if there are more pages after the current one.
    
    Args:
        page: Current page number (1-indexed)
        per_page: Items per page
        total: Total number of items
        
    Returns:
        True if there's a next page
    """
    return page * per_page < total


def has_prev_page(page: int) -> bool:
    """
    Check if there are pages before the current one.
    
    Args:
        page: Current page number (1-indexed)
        
    Returns:
        True if there's a previous page
    """
    return page > 1


# =============================================================================
# Paginated Result Container
# =============================================================================


@dataclass
class PaginatedResult(Generic[T]):
    """
    Generic container for paginated query results.
    
    This is the single source of truth for pagination across all services.
    Use the `create()` factory method to construct instances with computed fields.
    
    Attributes:
        items: List of items for the current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        per_page: Items per page
        pages: Total number of pages
        has_next: Whether there's a next page
        has_prev: Whether there's a previous page
    """
    
    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        per_page: int,
    ) -> "PaginatedResult[T]":
        """
        Create a paginated result with computed navigation fields.
        
        Args:
            items: Items for the current page
            total: Total number of items
            page: Current page number (1-indexed)
            per_page: Items per page
            
        Returns:
            PaginatedResult with all fields computed
        """
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=calculate_pages(total, per_page),
            has_next=has_next_page(page, per_page, total),
            has_prev=has_prev_page(page),
        )
    
    @classmethod
    def empty(cls, page: int = 1, per_page: int = 20) -> "PaginatedResult[T]":
        """
        Create an empty paginated result.
        
        Args:
            page: Page number
            per_page: Items per page
            
        Returns:
            Empty PaginatedResult
        """
        return cls.create(items=[], total=0, page=page, per_page=per_page)


# =============================================================================
# Backward Compatibility Alias
# =============================================================================


# Alias for backward compatibility with older code
# Use PaginatedResult directly in new code
PaginatedPosts = PaginatedResult

