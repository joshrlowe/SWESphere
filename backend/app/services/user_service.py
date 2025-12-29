"""
User service.

Core user operations including:
- Profile retrieval and updates
- Avatar management (delegated to AvatarService)
- Follow/unfollow relationships
- User discovery and search

Caching Strategy:
- Profiles: Cache-aside with 5 min TTL
- Follower/following counts: Write-through counters
- Username lookups: Cached ID mappings
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.pagination import PaginatedResult, calculate_skip
from app.core.redis_keys import CacheKeys
from app.core.security import hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserPasswordUpdate, UserUpdate
from app.services.avatar_service import AvatarService
from app.services.exceptions import (
    CannotFollowSelfError,
    PasswordMismatchError,
    UserNotFoundError,
    UsernameConflictError,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fastapi import UploadFile

    from app.models.user import User
    from app.services.cache_invalidation import CacheInvalidator
    from app.services.cache_service import CacheService
    from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

USER_PROFILE_TTL = 300  # 5 minutes
USER_COUNTS_TTL = 3600  # 1 hour


# =============================================================================
# Service
# =============================================================================


class UserService:
    """
    Service for user operations.

    This class orchestrates user-related business logic, delegating
    specialized concerns to dedicated services:
    - Avatar handling → AvatarService
    - Caching → CacheService + CacheInvalidator
    - Notifications → NotificationService
    - Data access → UserRepository

    Design Principles:
    - Single Responsibility: Orchestrates user operations
    - Dependency Injection: All dependencies are injectable
    - Graceful Degradation: Works without optional dependencies
    """

    def __init__(
        self,
        user_repo: UserRepository,
        notification_service: "NotificationService | None" = None,
        avatar_service: AvatarService | None = None,
        cache: "CacheService | None" = None,
        cache_invalidator: "CacheInvalidator | None" = None,
    ) -> None:
        """
        Initialize user service.

        Args:
            user_repo: Repository for user data access
            notification_service: Service for sending notifications
            avatar_service: Service for avatar operations
            cache: Service for cache operations
            cache_invalidator: Service for cache invalidation
        """
        self._repo = user_repo
        self._notifications = notification_service
        self._avatar = avatar_service or AvatarService()
        self._cache = cache
        self._invalidator = cache_invalidator

    # =========================================================================
    # Properties (backward compatibility)
    # =========================================================================

    @property
    def user_repo(self) -> UserRepository:
        """User repository (for backward compatibility)."""
        return self._repo

    @property
    def notification_service(self) -> "NotificationService | None":
        """Notification service (for backward compatibility)."""
        return self._notifications

    # =========================================================================
    # User Retrieval
    # =========================================================================

    async def get_user_by_id(self, user_id: int) -> "User":
        """
        Get user by ID.

        Args:
            user_id: User's ID

        Returns:
            User object

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        return user

    async def get_user_by_username(self, username: str) -> "User":
        """
        Get user by username with cache optimization.

        Uses username→ID cache mapping for faster lookups.

        Args:
            username: User's username

        Returns:
            User object

        Raises:
            UserNotFoundError: If user not found
        """
        # Try cache first
        user = await self._get_user_from_username_cache(username)
        if user:
            return user

        # Cache miss - query database
        user = await self._repo.get_by_username(username)
        if not user:
            raise UserNotFoundError()

        # Cache the mapping
        await self._cache_username_mapping(username, user.id)
        return user

    async def _get_user_from_username_cache(self, username: str) -> "User | None":
        """Attempt to get user via cached username→ID mapping."""
        if not self._cache:
            return None

        cached_id = await self._cache.get(CacheKeys.user_by_username(username))
        if not cached_id:
            return None

        try:
            user_id = int(cached_id)
            user = await self._repo.get_by_id(user_id)
            if user:
                logger.debug("Cache HIT: username=%s", username)
                return user
        except ValueError:
            pass

        return None

    async def _cache_username_mapping(self, username: str, user_id: int) -> None:
        """Cache username→ID mapping."""
        if self._cache:
            await self._cache.set(
                CacheKeys.user_by_username(username),
                str(user_id),
                USER_PROFILE_TTL,
            )
            logger.debug("Cache SET: username=%s → id=%d", username, user_id)

    # =========================================================================
    # Profile Caching
    # =========================================================================

    async def get_user_profile_cached(self, user_id: int) -> dict[str, Any] | None:
        """
        Get cached user profile.

        Returns:
            Cached profile dict, or None if not cached
        """
        if not self._cache:
            return None
        return await self._cache.get_json(CacheKeys.user(user_id))

    async def cache_user_profile(self, user: "User") -> None:
        """Cache user profile and username mapping."""
        if not self._cache:
            return

        profile = self._serialize_user_profile(user)
        await self._cache.set_json(CacheKeys.user(user.id), profile, USER_PROFILE_TTL)
        await self._cache_username_mapping(user.username, user.id)

    @staticmethod
    def _serialize_user_profile(user: "User") -> dict[str, Any]:
        """Serialize user to cacheable dict."""
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "bio": user.bio,
            "avatar_url": user.avatar_url,
            "location": getattr(user, "location", None),
            "website": getattr(user, "website", None),
            "followers_count": user.followers_count,
            "following_count": user.following_count,
            "posts_count": getattr(user, "posts_count", 0),
            "is_verified": getattr(user, "is_verified", False),
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

    # =========================================================================
    # Profile Management
    # =========================================================================

    async def update_profile(self, user_id: int, data: UserUpdate) -> "User":
        """
        Update user profile.

        Args:
            user_id: User to update
            data: Profile fields to update

        Returns:
            Updated user

        Raises:
            UserNotFoundError: If user not found
            UsernameConflictError: If username taken
        """
        current_user = await self._repo.get_by_id(user_id)
        old_username = current_user.username if current_user else None

        await self._validate_username_available(user_id, data.username)

        user = await self._repo.update(user_id, **data.model_dump(exclude_unset=True))
        if not user:
            raise UserNotFoundError()

        await self._invalidate_user_cache(user_id, old_username, data.username)

        logger.info("Profile updated: user_id=%d", user_id)
        return user

    async def _validate_username_available(
        self,
        user_id: int,
        new_username: str | None,
    ) -> None:
        """Validate username is available for this user."""
        if not new_username:
            return

        existing = await self._repo.get_by_username(new_username)
        if existing and existing.id != user_id:
            raise UsernameConflictError()

    async def _invalidate_user_cache(
        self,
        user_id: int,
        old_username: str | None,
        new_username: str | None,
    ) -> None:
        """Invalidate user cache entries."""
        if not self._invalidator:
            return

        await self._invalidator.invalidate_user(user_id, old_username)
        if new_username and new_username != old_username:
            await self._invalidator.invalidate_user(user_id, new_username)

    async def update_password(self, user_id: int, data: UserPasswordUpdate) -> None:
        """
        Update user password.

        Args:
            user_id: User to update
            data: Current and new password

        Raises:
            UserNotFoundError: If user not found
            PasswordMismatchError: If current password wrong
        """
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        if not verify_password(data.current_password, user.password_hash):
            raise PasswordMismatchError()

        new_hash = hash_password(data.new_password)
        await self._repo.update(user_id, password_hash=new_hash)

        logger.info("Password updated: user_id=%d", user_id)

    # =========================================================================
    # Avatar Management (delegated to AvatarService)
    # =========================================================================

    async def upload_avatar(self, user_id: int, file: "UploadFile") -> str:
        """
        Upload new avatar for user.

        Args:
            user_id: User uploading avatar
            file: Uploaded image file

        Returns:
            URL of uploaded avatar

        Raises:
            UserNotFoundError: If user not found
            InvalidAvatarTypeError: If file type invalid
            AvatarTooLargeError: If file too large
        """
        user = await self.get_user_by_id(user_id)
        avatar_url = await self._avatar.replace(user_id, file, user.avatar_url)
        await self._repo.update(user_id, avatar_url=avatar_url)

        logger.info("Avatar uploaded: user_id=%d", user_id)
        return avatar_url

    async def delete_avatar(self, user_id: int) -> None:
        """
        Delete user's avatar.

        Args:
            user_id: User whose avatar to delete

        Raises:
            UserNotFoundError: If user not found
        """
        user = await self.get_user_by_id(user_id)
        await self._avatar.delete_for_user(user)
        await self._repo.update(user_id, avatar_url=None)

        logger.info("Avatar deleted: user_id=%d", user_id)

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
            True if follow created, False if already following

        Raises:
            CannotFollowSelfError: If attempting self-follow
            UserNotFoundError: If followed user not found
        """
        self._validate_not_self_follow(follower_id, followed_id)
        await self._ensure_user_exists(followed_id)

        success = await self._repo.follow(follower_id, followed_id)

        if success:
            logger.info("Follow: %d → %d", follower_id, followed_id)
            await self._on_follow_success(follower_id, followed_id)

        return success

    async def _on_follow_success(self, follower_id: int, followed_id: int) -> None:
        """Handle successful follow event."""
        if self._invalidator:
            await self._invalidator.on_follow(follower_id, followed_id)
        await self._send_follow_notification(follower_id, followed_id)

    async def unfollow_user(self, follower_id: int, followed_id: int) -> bool:
        """
        Unfollow a user.

        Args:
            follower_id: User who is unfollowing
            followed_id: User to unfollow

        Returns:
            True if unfollowed, False if wasn't following
        """
        success = await self._repo.unfollow(follower_id, followed_id)

        if success:
            logger.info("Unfollow: %d → %d", follower_id, followed_id)
            if self._invalidator:
                await self._invalidator.on_unfollow(follower_id, followed_id)

        return success

    async def is_following(self, follower_id: int, followed_id: int) -> bool:
        """Check if user is following another."""
        return await self._repo.is_following(follower_id, followed_id)

    @staticmethod
    def _validate_not_self_follow(follower_id: int, followed_id: int) -> None:
        """Raise if attempting self-follow."""
        if follower_id == followed_id:
            raise CannotFollowSelfError()

    async def _ensure_user_exists(self, user_id: int) -> None:
        """Raise if user doesn't exist."""
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()

    async def _send_follow_notification(
        self,
        follower_id: int,
        followed_id: int,
    ) -> None:
        """Send follow notification if service available."""
        if not self._notifications:
            return

        follower = await self._repo.get_by_id(follower_id)
        if not follower:
            return

        await self._notifications.notify_new_follower(
            user_id=followed_id,
            follower_id=follower_id,
            follower_username=follower.username,
        )

    # =========================================================================
    # Follower/Following Counts (with caching)
    # =========================================================================

    async def get_followers_count(self, user_id: int) -> int:
        """Get follower count with cache support."""
        return await self._get_cached_count(
            cache_key=CacheKeys.user_followers_count(user_id),
            user_id=user_id,
            count_attr="followers_count",
        )

    async def get_following_count(self, user_id: int) -> int:
        """Get following count with cache support."""
        return await self._get_cached_count(
            cache_key=CacheKeys.user_following_count(user_id),
            user_id=user_id,
            count_attr="following_count",
        )

    async def _get_cached_count(
        self,
        cache_key: str,
        user_id: int,
        count_attr: str,
    ) -> int:
        """
        Get count with cache-aside pattern.

        Checks cache first, falls back to database, warms cache on miss.
        """
        # Try cache
        if self._cache:
            cached = await self._cache.get_counter(cache_key)
            if cached is not None:
                return cached

        # Query database
        user = await self._repo.get_by_id(user_id)
        count = getattr(user, count_attr, 0) if user else 0

        # Warm cache
        if self._cache and user:
            await self._cache.set_counter(cache_key, count, USER_COUNTS_TTL)

        return count

    # =========================================================================
    # Follower/Following Lists
    # =========================================================================

    async def get_followers(
        self,
        user_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult["User"]:
        """Get paginated list of user's followers."""
        return await self._paginated_query(
            lambda skip, limit: self._repo.get_followers_paginated(
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
    ) -> PaginatedResult["User"]:
        """Get paginated list of users being followed."""
        return await self._paginated_query(
            lambda skip, limit: self._repo.get_following_paginated(
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
    ) -> PaginatedResult["User"]:
        """Search users by username or display name."""
        return await self._paginated_query(
            lambda skip, limit: self._repo.search_users(query, skip=skip, limit=limit),
            page=page,
            per_page=per_page,
        )

    async def get_suggested_users(
        self,
        user_id: int,
        *,
        limit: int = 10,
    ) -> list["User"]:
        """
        Get suggested users to follow.

        Returns popular users not already followed.
        """
        following_ids = await self._repo.get_following_ids(user_id)
        exclude_ids = {user_id, *following_ids}

        suggestions = await self._repo.get_popular_users(
            exclude_ids=exclude_ids,
            limit=limit,
        )

        return list(suggestions)

    # =========================================================================
    # Pagination Helper
    # =========================================================================

    @staticmethod
    async def _paginated_query(
        query_fn,
        page: int,
        per_page: int,
    ) -> PaginatedResult:
        """Execute paginated query and wrap results."""
        skip = calculate_skip(page, per_page)
        items, total = await query_fn(skip, per_page)

        return PaginatedResult.create(
            items=list(items),
            total=total,
            page=page,
            per_page=per_page,
        )


# =============================================================================
# Backward Compatibility Exports
# =============================================================================

# Re-export exceptions for existing imports
from app.services.exceptions import (  # noqa: E402, F401
    CannotFollowSelfError,
    InvalidAvatarError,
    PasswordMismatchError,
    UserNotFoundError,
    UsernameConflictError,
)

# Re-export storage for existing imports
from app.services.storage import FileStorage, LocalFileStorage  # noqa: E402, F401

# Re-export AvatarConfig for existing imports (now in avatar_service)
from app.services.avatar_service import AvatarConfig  # noqa: E402, F401
