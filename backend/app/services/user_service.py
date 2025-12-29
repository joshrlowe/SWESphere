"""
User service.

Handles user profile management, avatar uploads, follow relationships,
and user discovery.
"""

import logging
import os
import uuid
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserPasswordUpdate, UserUpdate

logger = logging.getLogger(__name__)


# =============================================================================
# Response Types
# =============================================================================


@dataclass
class PaginatedUsers:
    """Paginated list of users."""

    users: list[User]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


# =============================================================================
# File Storage Protocol
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
    """Local filesystem storage for development."""

    def __init__(self, base_path: str, base_url: str) -> None:
        self.base_path = base_path
        self.base_url = base_url
        os.makedirs(base_path, exist_ok=True)

    async def upload(self, file: UploadFile, path: str) -> str:
        """Upload file to local filesystem."""
        full_path = os.path.join(self.base_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        content = await file.read()
        with open(full_path, "wb") as f:
            f.write(content)

        return f"{self.base_url}/{path}"

    async def delete(self, path: str) -> bool:
        """Delete file from local filesystem."""
        full_path = os.path.join(self.base_path, path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False


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

    # Allowed avatar file types
    ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB

    def __init__(
        self,
        user_repo: UserRepository,
        notification_service: "NotificationService | None" = None,
        file_storage: FileStorage | None = None,
    ) -> None:
        """
        Initialize user service.

        Args:
            user_repo: User repository for data access
            notification_service: Optional notification service for follow events
            file_storage: Optional file storage for avatar uploads
        """
        self.user_repo = user_repo
        self.notification_service = notification_service
        self.file_storage = file_storage or LocalFileStorage(
            base_path="./uploads/avatars",
            base_url="/uploads/avatars",
        )

    # =========================================================================
    # User Retrieval
    # =========================================================================

    async def get_user_by_id(self, user_id: int) -> User:
        """
        Get user by ID.

        Args:
            user_id: User's ID

        Returns:
            User object

        Raises:
            HTTPException: If user not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def get_user_by_username(self, username: str) -> User:
        """
        Get user by username.

        Args:
            username: User's username

        Returns:
            User object

        Raises:
            HTTPException: If user not found
        """
        user = await self.user_repo.get_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
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
            HTTPException: If user not found or username taken
        """
        # Check if username is being changed and is available
        if data.username:
            existing = await self.user_repo.get_by_username(data.username)
            if existing and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )

        user = await self.user_repo.update(
            user_id,
            **data.model_dump(exclude_unset=True),
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        logger.info(f"Profile updated for user: {user_id}")
        return user

    async def update_password(
        self,
        user_id: int,
        data: UserPasswordUpdate,
    ) -> None:
        """
        Update user password.

        Args:
            user_id: User to update
            data: Current and new password

        Raises:
            HTTPException: If user not found or current password wrong
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        await self.user_repo.update(
            user_id,
            password_hash=hash_password(data.new_password),
        )

        logger.info(f"Password updated for user: {user_id}")

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
            HTTPException: If file type invalid or too large
        """
        # Validate file type
        if file.content_type not in self.ALLOWED_AVATAR_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(self.ALLOWED_AVATAR_TYPES)}",
            )

        # Check file size
        content = await file.read()
        await file.seek(0)  # Reset for later read

        if len(content) > self.MAX_AVATAR_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {self.MAX_AVATAR_SIZE // 1024 // 1024}MB",
            )

        # Get user (verify exists)
        user = await self.get_user_by_id(user_id)

        # Delete old avatar if exists
        if user.avatar_url and self.file_storage:
            # Extract path from URL
            old_path = user.avatar_url.split("/uploads/avatars/")[-1]
            await self.file_storage.delete(old_path)

        # Generate unique filename
        ext = file.filename.split(".")[-1] if file.filename else "jpg"
        filename = f"{user_id}/{uuid.uuid4()}.{ext}"

        # Upload new avatar
        avatar_url = await self.file_storage.upload(file, filename)

        # Update user record
        await self.user_repo.update(user_id, avatar_url=avatar_url)

        logger.info(f"Avatar uploaded for user: {user_id}")
        return avatar_url

    async def delete_avatar(self, user_id: int) -> None:
        """Delete user's avatar and reset to default."""
        user = await self.get_user_by_id(user_id)

        if user.avatar_url and self.file_storage:
            old_path = user.avatar_url.split("/uploads/avatars/")[-1]
            await self.file_storage.delete(old_path)

        await self.user_repo.update(user_id, avatar_url=None)
        logger.info(f"Avatar deleted for user: {user_id}")

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
            True if follow was created

        Raises:
            HTTPException: If can't follow self or user not found
        """
        if follower_id == followed_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot follow yourself",
            )

        # Verify followed user exists
        followed = await self.user_repo.get_by_id(followed_id)
        if not followed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Create follow relationship
        success = await self.user_repo.follow(follower_id, followed_id)

        if success and self.notification_service:
            # Get follower for notification
            follower = await self.user_repo.get_by_id(follower_id)
            if follower:
                await self.notification_service.notify_new_follower(
                    user_id=followed_id,
                    follower_id=follower_id,
                    follower_username=follower.username,
                )

        if success:
            logger.info(f"User {follower_id} followed user {followed_id}")

        return success

    async def unfollow_user(self, follower_id: int, followed_id: int) -> bool:
        """
        Unfollow a user.

        Args:
            follower_id: User who is unfollowing
            followed_id: User to unfollow

        Returns:
            True if follow was removed
        """
        success = await self.user_repo.unfollow(follower_id, followed_id)

        if success:
            logger.info(f"User {follower_id} unfollowed user {followed_id}")

        return success

    async def is_following(self, follower_id: int, followed_id: int) -> bool:
        """Check if user is following another user."""
        return await self.user_repo.is_following(follower_id, followed_id)

    # =========================================================================
    # Followers/Following Lists
    # =========================================================================

    async def get_followers(
        self,
        user_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedUsers:
        """
        Get user's followers with pagination.

        Args:
            user_id: User to get followers for
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            PaginatedUsers with followers and metadata
        """
        skip = (page - 1) * per_page
        followers, total = await self.user_repo.get_followers_paginated(
            user_id, skip=skip, limit=per_page
        )

        return PaginatedUsers(
            users=list(followers),
            total=total,
            page=page,
            per_page=per_page,
            has_next=skip + len(followers) < total,
            has_prev=page > 1,
        )

    async def get_following(
        self,
        user_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedUsers:
        """
        Get users that this user is following with pagination.

        Args:
            user_id: User to get following for
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            PaginatedUsers with following and metadata
        """
        skip = (page - 1) * per_page
        following, total = await self.user_repo.get_following_paginated(
            user_id, skip=skip, limit=per_page
        )

        return PaginatedUsers(
            users=list(following),
            total=total,
            page=page,
            per_page=per_page,
            has_next=skip + len(following) < total,
            has_prev=page > 1,
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
    ) -> PaginatedUsers:
        """
        Search users by username or display name.

        Args:
            query: Search query
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            PaginatedUsers with search results
        """
        skip = (page - 1) * per_page
        users, total = await self.user_repo.search_users(
            query, skip=skip, limit=per_page
        )

        return PaginatedUsers(
            users=list(users),
            total=total,
            page=page,
            per_page=per_page,
            has_next=skip + len(users) < total,
            has_prev=page > 1,
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
        # Get IDs of users already being followed
        following_ids = await self.user_repo.get_following_ids(user_id)

        # Get popular users not followed
        suggestions = await self.user_repo.get_popular_users(
            exclude_ids={user_id, *following_ids},
            limit=limit,
        )

        return list(suggestions)


# For type hints
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.notification_service import NotificationService
