"""
User service.

Handles user profile management, avatar uploads, follow relationships,
and user discovery.
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable, Protocol, TypeVar
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.core.pagination import PaginatedResult, calculate_skip
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserPasswordUpdate, UserUpdate

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


# =============================================================================
# Type Aliases
# =============================================================================

T = TypeVar("T")
PaginatedQuery = Callable[[int, int], Awaitable[tuple["Sequence[T]", int]]]


# =============================================================================
# Exceptions
# =============================================================================


class UserNotFoundError(HTTPException):
    """Raised when a requested user does not exist."""

    def __init__(self, detail: str = "User not found") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class InvalidAvatarError(HTTPException):
    """Raised when avatar file validation fails."""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UsernameConflictError(HTTPException):
    """Raised when username is already taken."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )


class PasswordMismatchError(HTTPException):
    """Raised when current password verification fails."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )


class CannotFollowSelfError(HTTPException):
    """Raised when a user attempts to follow themselves."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself",
        )


# =============================================================================
# File Storage Protocol & Implementation
# =============================================================================


class FileStorage(Protocol):
    """Protocol for file storage backends."""

    async def upload(self, file: UploadFile, path: str) -> str:
        """Upload file and return URL."""
        ...

    async def delete(self, path: str) -> bool:
        """Delete file at path."""
        ...


class LocalFileStorage:
    """
    Local filesystem storage for development.

    Stores files in a local directory and returns URLs relative to base_url.
    """

    def __init__(self, base_path: Path, base_url: str) -> None:
        """
        Initialize local file storage.

        Args:
            base_path: Local filesystem path for storage
            base_url: Base URL prefix for generated file URLs
        """
        self.base_path = base_path
        self.base_url = base_url.rstrip("/")
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload(self, file: UploadFile, path: str) -> str:
        """Upload file to local filesystem."""
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        content = await file.read()
        full_path.write_bytes(content)

        return f"{self.base_url}/{path}"

    async def delete(self, path: str) -> bool:
        """Delete file from local filesystem."""
        full_path = self.base_path / path
        if full_path.exists():
            full_path.unlink()
            return True
        return False


# =============================================================================
# Avatar Configuration
# =============================================================================


class AvatarConfig:
    """Configuration for avatar uploads."""

    def __init__(
        self,
        allowed_types: set[str] | None = None,
        max_size_bytes: int | None = None,
        storage_path_prefix: str = "/uploads/avatars",
    ) -> None:
        self.allowed_types = allowed_types or set(settings.ALLOWED_IMAGE_TYPES)
        self.max_size_bytes = max_size_bytes or settings.AVATAR_MAX_SIZE
        self.storage_path_prefix = storage_path_prefix

    @property
    def max_size_mb(self) -> float:
        """Get max size in megabytes for display."""
        return self.max_size_bytes / (1024 * 1024)

    @property
    def allowed_types_display(self) -> str:
        """Get comma-separated list of allowed types for error messages."""
        return ", ".join(sorted(self.allowed_types))

    def extract_path_from_url(self, url: str) -> str:
        """
        Extract the storage path from an avatar URL.

        Args:
            url: Full avatar URL

        Returns:
            Relative storage path
        """
        marker = f"{self.storage_path_prefix}/"
        if marker in url:
            return url.split(marker)[-1]
        # Fallback: return everything after the last slash
        return url.rsplit("/", 1)[-1]


# =============================================================================
# Service
# =============================================================================


class UserService:
    """
    Service for user operations.

    Handles:
    - User profile retrieval and updates
    - Avatar uploads
    - Follow/unfollow relationships
    - User discovery and search
    """

    # Default configuration
    DEFAULT_AVATAR_PATH = Path("./uploads/avatars")
    DEFAULT_AVATAR_URL = "/uploads/avatars"

    def __init__(
        self,
        user_repo: UserRepository,
        notification_service: NotificationService | None = None,
        file_storage: FileStorage | None = None,
        avatar_config: AvatarConfig | None = None,
    ) -> None:
        """
        Initialize user service.

        Args:
            user_repo: User repository for data access
            notification_service: Optional notification service for follow events
            file_storage: Optional file storage for avatar uploads
            avatar_config: Optional avatar upload configuration
        """
        self._user_repo = user_repo
        self._notification_service = notification_service
        self._avatar_config = avatar_config or AvatarConfig()
        self._file_storage = file_storage or LocalFileStorage(
            base_path=self.DEFAULT_AVATAR_PATH,
            base_url=self.DEFAULT_AVATAR_URL,
        )

    # =========================================================================
    # Properties (for backward compatibility)
    # =========================================================================

    @property
    def user_repo(self) -> UserRepository:
        """User repository accessor for backward compatibility."""
        return self._user_repo

    @property
    def notification_service(self) -> NotificationService | None:
        """Notification service accessor for backward compatibility."""
        return self._notification_service

    @property
    def file_storage(self) -> FileStorage:
        """File storage accessor for backward compatibility."""
        return self._file_storage

    # =========================================================================
    # User Retrieval
    # =========================================================================

    async def get_user_by_id(self, user_id: int) -> User:
        """
        Get user by ID, raising if not found.

        Args:
            user_id: User's ID

        Returns:
            User object

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        return user

    async def get_user_by_username(self, username: str) -> User:
        """
        Get user by username, raising if not found.

        Args:
            username: User's username

        Returns:
            User object

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self._user_repo.get_by_username(username)
        if not user:
            raise UserNotFoundError()
        return user

    # =========================================================================
    # Profile Management
    # =========================================================================

    async def update_profile(self, user_id: int, data: UserUpdate) -> User:
        """
        Update user profile.

        Args:
            user_id: User to update
            data: Fields to update

        Returns:
            Updated User

        Raises:
            UserNotFoundError: If user not found
            UsernameConflictError: If username already taken by another user
        """
        await self._validate_username_availability(user_id, data.username)

        user = await self._user_repo.update(
            user_id,
            **data.model_dump(exclude_unset=True),
        )

        if not user:
            raise UserNotFoundError()

        logger.info("Profile updated for user: %d", user_id)
        return user

    async def _validate_username_availability(
        self,
        user_id: int,
        new_username: str | None,
    ) -> None:
        """
        Check if a username is available for a user.

        Args:
            user_id: ID of user attempting to use the username
            new_username: Username to check (None means no change)

        Raises:
            UsernameConflictError: If username is taken by another user
        """
        if not new_username:
            return

        existing = await self._user_repo.get_by_username(new_username)
        if existing and existing.id != user_id:
            raise UsernameConflictError()

    async def update_password(self, user_id: int, data: UserPasswordUpdate) -> None:
        """
        Update user password.

        Args:
            user_id: User to update
            data: Current and new password

        Raises:
            UserNotFoundError: If user not found
            PasswordMismatchError: If current password is incorrect
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        if not verify_password(data.current_password, user.password_hash):
            raise PasswordMismatchError()

        new_hash = hash_password(data.new_password)
        await self._user_repo.update(user_id, password_hash=new_hash)

        logger.info("Password updated for user: %d", user_id)

    # =========================================================================
    # Avatar Management
    # =========================================================================

    async def upload_avatar(self, user_id: int, file: UploadFile) -> str:
        """
        Upload new avatar for user.

        Args:
            user_id: User uploading avatar
            file: Uploaded image file

        Returns:
            URL of uploaded avatar

        Raises:
            InvalidAvatarError: If file type invalid or too large
            UserNotFoundError: If user not found
        """
        await self._validate_avatar(file)
        user = await self.get_user_by_id(user_id)

        await self._delete_user_avatar(user)
        avatar_url = await self._save_avatar(user_id, file)
        await self._user_repo.update(user_id, avatar_url=avatar_url)

        logger.info("Avatar uploaded for user: %d", user_id)
        return avatar_url

    async def delete_avatar(self, user_id: int) -> None:
        """
        Delete user's avatar and reset to default.

        Args:
            user_id: User whose avatar to delete

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.get_user_by_id(user_id)

        await self._delete_user_avatar(user)
        await self._user_repo.update(user_id, avatar_url=None)

        logger.info("Avatar deleted for user: %d", user_id)

    async def _validate_avatar(self, file: UploadFile) -> None:
        """
        Validate avatar file type and size.

        Args:
            file: Uploaded file to validate

        Raises:
            InvalidAvatarError: If validation fails
        """
        self._validate_avatar_content_type(file)
        await self._validate_avatar_size(file)

    def _validate_avatar_content_type(self, file: UploadFile) -> None:
        """Validate avatar content type."""
        if file.content_type not in self._avatar_config.allowed_types:
            raise InvalidAvatarError(
                f"Invalid file type. Allowed: {self._avatar_config.allowed_types_display}"
            )

    async def _validate_avatar_size(self, file: UploadFile) -> None:
        """Validate avatar file size."""
        content = await file.read()
        await file.seek(0)

        if len(content) > self._avatar_config.max_size_bytes:
            raise InvalidAvatarError(
                f"File too large. Maximum size: {self._avatar_config.max_size_mb:.0f}MB"
            )

    async def _delete_user_avatar(self, user: User) -> None:
        """Delete user's current avatar file if it exists."""
        if not user.avatar_url:
            return

        old_path = self._avatar_config.extract_path_from_url(user.avatar_url)
        await self._file_storage.delete(old_path)

    async def _save_avatar(self, user_id: int, file: UploadFile) -> str:
        """
        Save avatar file and return its URL.

        Args:
            user_id: User ID for path organization
            file: Uploaded file

        Returns:
            URL of the saved avatar
        """
        filename = self._generate_avatar_filename(user_id, file.filename)
        return await self._file_storage.upload(file, filename)

    def _generate_avatar_filename(
        self,
        user_id: int,
        original_filename: str | None,
    ) -> str:
        """
        Generate a unique filename for an avatar.

        Args:
            user_id: User ID for directory organization
            original_filename: Original filename to extract extension

        Returns:
            Unique filename with path
        """
        extension = self._extract_file_extension(original_filename)
        unique_id = uuid4()
        return f"{user_id}/{unique_id}.{extension}"

    @staticmethod
    def _extract_file_extension(filename: str | None) -> str:
        """
        Extract file extension from filename.

        Args:
            filename: Original filename

        Returns:
            File extension without dot, defaults to 'jpg'
        """
        if not filename:
            return "jpg"

        if "." in filename:
            return filename.rsplit(".", 1)[-1].lower()

        # Try to guess from filename using mimetypes
        guessed_type, _ = mimetypes.guess_type(filename)
        if guessed_type:
            extension = mimetypes.guess_extension(guessed_type)
            if extension:
                return extension.lstrip(".")

        return "jpg"

    # =========================================================================
    # Follow Relationships
    # =========================================================================

    async def follow_user(self, follower_id: int, followed_id: int) -> bool:
        """
        Follow another user.

        Args:
            follower_id: User who is following
            followed_id: User to follow

        Returns:
            True if follow was created, False if already following

        Raises:
            CannotFollowSelfError: If attempting to follow self
            UserNotFoundError: If followed user not found
        """
        self._validate_not_self_follow(follower_id, followed_id)
        await self._ensure_user_exists(followed_id)

        success = await self._user_repo.follow(follower_id, followed_id)

        if success:
            logger.info("User %d followed user %d", follower_id, followed_id)
            await self._send_follow_notification(follower_id, followed_id)

        return success

    async def unfollow_user(self, follower_id: int, followed_id: int) -> bool:
        """
        Unfollow a user.

        Args:
            follower_id: User who is unfollowing
            followed_id: User to unfollow

        Returns:
            True if follow was removed, False if wasn't following
        """
        success = await self._user_repo.unfollow(follower_id, followed_id)

        if success:
            logger.info("User %d unfollowed user %d", follower_id, followed_id)

        return success

    async def is_following(self, follower_id: int, followed_id: int) -> bool:
        """Check if user is following another user."""
        return await self._user_repo.is_following(follower_id, followed_id)

    @staticmethod
    def _validate_not_self_follow(follower_id: int, followed_id: int) -> None:
        """Raise if user is attempting to follow themselves."""
        if follower_id == followed_id:
            raise CannotFollowSelfError()

    async def _ensure_user_exists(self, user_id: int) -> None:
        """Raise UserNotFoundError if user doesn't exist."""
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()

    async def _send_follow_notification(
        self,
        follower_id: int,
        followed_id: int,
    ) -> None:
        """Send notification about new follower if notification service available."""
        if not self._notification_service:
            return

        follower = await self._user_repo.get_by_id(follower_id)
        if not follower:
            return

        await self._notification_service.notify_new_follower(
            user_id=followed_id,
            follower_id=follower_id,
            follower_username=follower.username,
        )

    # =========================================================================
    # Followers/Following Lists
    # =========================================================================

    async def get_followers(
        self,
        user_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult[User]:
        """
        Get user's followers with pagination.

        Args:
            user_id: User to get followers for
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            PaginatedResult with followers and metadata
        """
        return await self._paginate(
            query_fn=lambda skip, limit: self._user_repo.get_followers_paginated(
                user_id, skip=skip, limit=limit
            ),
            page=page,
            per_page=per_page,
        )

    async def get_following(
        self,
        user_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult[User]:
        """
        Get users that this user is following with pagination.

        Args:
            user_id: User to get following for
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            PaginatedResult with following and metadata
        """
        return await self._paginate(
            query_fn=lambda skip, limit: self._user_repo.get_following_paginated(
                user_id, skip=skip, limit=limit
            ),
            page=page,
            per_page=per_page,
        )

    # =========================================================================
    # User Discovery
    # =========================================================================

    async def search_users(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult[User]:
        """
        Search users by username or display name.

        Args:
            query: Search query
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            PaginatedResult with search results
        """
        return await self._paginate(
            query_fn=lambda skip, limit: self._user_repo.search_users(
                query, skip=skip, limit=limit
            ),
            page=page,
            per_page=per_page,
        )

    async def get_suggested_users(
        self,
        user_id: int,
        *,
        limit: int = 10,
    ) -> list[User]:
        """
        Get suggested users to follow.

        Suggests popular users that the current user isn't following.

        Args:
            user_id: Current user
            limit: Max suggestions to return

        Returns:
            List of suggested User objects
        """
        following_ids = await self._user_repo.get_following_ids(user_id)
        exclude_ids = {user_id, *following_ids}

        suggestions = await self._user_repo.get_popular_users(
            exclude_ids=exclude_ids,
            limit=limit,
        )

        return list(suggestions)

    # =========================================================================
    # Pagination Helper
    # =========================================================================

    @staticmethod
    async def _paginate(
        query_fn: Callable[[int, int], Awaitable[tuple[Sequence[T], int]]],
        page: int,
        per_page: int,
    ) -> PaginatedResult[T]:
        """
        Execute a paginated query and wrap results.

        Args:
            query_fn: Async function that takes (skip, limit) and returns (items, total)
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            PaginatedResult with items and metadata
        """
        skip = calculate_skip(page, per_page)
        items, total = await query_fn(skip, per_page)

        return PaginatedResult.create(
            items=list(items),
            total=total,
            page=page,
            per_page=per_page,
        )
