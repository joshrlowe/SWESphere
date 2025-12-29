"""
Service layer exceptions.

Centralized domain exceptions for all services. Using HTTPException
subclasses allows these to propagate directly to API responses.

Exception Hierarchy:
- UserNotFoundError: 404 - User doesn't exist
- InvalidAvatarError: 400 - Avatar validation failed
- UsernameConflictError: 400 - Username already taken
- PasswordMismatchError: 400 - Password verification failed
- CannotFollowSelfError: 400 - Self-follow attempt
- PostNotFoundError: 404 - Post doesn't exist
- UnauthorizedError: 403 - Not authorized for action
"""

from fastapi import HTTPException, status


# =============================================================================
# Base Exception
# =============================================================================


class ServiceError(HTTPException):
    """Base exception for service layer errors."""

    def __init__(
        self,
        status_code: int,
        detail: str,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)


# =============================================================================
# User Exceptions
# =============================================================================


class UserNotFoundError(ServiceError):
    """Raised when a requested user does not exist."""

    def __init__(self, detail: str = "User not found") -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class UsernameConflictError(ServiceError):
    """Raised when username is already taken by another user."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )


class PasswordMismatchError(ServiceError):
    """Raised when current password verification fails."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )


class CannotFollowSelfError(ServiceError):
    """Raised when a user attempts to follow themselves."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself",
        )


# =============================================================================
# Avatar Exceptions
# =============================================================================


class InvalidAvatarError(ServiceError):
    """Raised when avatar file validation fails."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class AvatarTooLargeError(InvalidAvatarError):
    """Raised when avatar file exceeds size limit."""

    def __init__(self, max_size_mb: float) -> None:
        super().__init__(
            detail=f"File too large. Maximum size: {max_size_mb:.0f}MB",
        )


class InvalidAvatarTypeError(InvalidAvatarError):
    """Raised when avatar file type is not allowed."""

    def __init__(self, allowed_types: str) -> None:
        super().__init__(
            detail=f"Invalid file type. Allowed: {allowed_types}",
        )


# =============================================================================
# Post Exceptions
# =============================================================================


class PostNotFoundError(ServiceError):
    """Raised when a requested post does not exist."""

    def __init__(self, detail: str = "Post not found") -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class UnauthorizedPostActionError(ServiceError):
    """Raised when user is not authorized to modify a post."""

    def __init__(self, action: str = "modify") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not authorized to {action} this post",
        )


# =============================================================================
# Content Exceptions
# =============================================================================


class EmptyContentError(ServiceError):
    """Raised when content is empty or whitespace-only."""

    def __init__(self, content_type: str = "Content") -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{content_type} cannot be empty",
        )


class ContentTooLongError(ServiceError):
    """Raised when content exceeds maximum length."""

    def __init__(self, content_type: str, max_length: int) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{content_type} exceeds {max_length} characters",
        )

