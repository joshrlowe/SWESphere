"""
User service for profile management, social relationships, and user discovery.

Responsibilities:
- Profile CRUD operations with caching
- Avatar management (delegated to AvatarService)
- Follow/unfollow relationships with notifications
- User search and discovery

Caching:
- Profiles: Cache-aside with 5-minute TTL
- Counts: Write-through counters with 1-hour TTL
- Username lookups: Cached ID mappings
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any, TypedDict

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
    from fastapi import UploadFile

    from app.models.user import User
    from app.services.cache_invalidation import CacheInvalidator
    from app.services.cache_service import CacheService
    from app.services.notification_service import NotificationService


logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

PROFILE_CACHE_TTL = 300  # 5 minutes
COUNTS_CACHE_TTL = 3600  # 1 hour


# =============================================================================
# Types
# =============================================================================


class UserProfile(TypedDict):
    """Serialized user profile for caching."""

    id: int
    username: str
    email: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    location: str | None
    website: str | None
    followers_count: int
    following_count: int
    posts_count: int
    is_verified: bool
    created_at: str | None


class _CountType(Enum):
    """User count types for cache operations."""

    FOLLOWERS = "followers_count"
    FOLLOWING = "following_count"


# Type alias for paginated repository queries
PaginatedQuery = Callable[[int, int], Awaitable[tuple[Sequence[Any], int]]]


# =============================================================================
# Service
# =============================================================================


class UserService:
    """
    Orchestrates user operations with caching and notifications.

    Uses dependency injection for all collaborators, enabling testing
    and graceful degradation when optional services are unavailable.
    """

    __slots__ = ("_repo", "_notifications", "_avatar", "_cache", "_invalidator")

    def __init__(
        self,
        user_repo: UserRepository,
        notification_service: NotificationService | None = None,
        avatar_service: AvatarService | None = None,
        cache: CacheService | None = None,
        cache_invalidator: CacheInvalidator | None = None,
    ) -> None:
        self._repo = user_repo
        self._notifications = notification_service
        self._avatar = avatar_service or AvatarService()
        self._cache = cache
        self._invalidator = cache_invalidator

    # -------------------------------------------------------------------------
    # Properties (backward compatibility)
    # -------------------------------------------------------------------------

    @property
    def user_repo(self) -> UserRepository:
        """User repository accessor."""
        return self._repo

    @property
    def notification_service(self) -> NotificationService | None:
        """Notification service accessor."""
        return self._notifications

    # =========================================================================
    # User Retrieval
    # =========================================================================

    async def get_user_by_id(self, user_id: int) -> User:
        """
        Retrieve user by ID.

        Raises:
            UserNotFoundError: User does not exist.
        """
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        return user

    async def get_user_by_username(self, username: str) -> User:
        """
        Retrieve user by username with cache optimization.

        Raises:
            UserNotFoundError: User does not exist.
        """
        if cached_user := await self._lookup_cached_username(username):
            return cached_user

        user = await self._repo.get_by_username(username)
        if not user:
            raise UserNotFoundError()

        await self._cache_username_mapping(username, user.id)
        return user

    async def _lookup_cached_username(self, username: str) -> User | None:
        """Look up user via cached username→ID mapping."""
        if not self._cache:
            return None

        cached_id = await self._cache.get(CacheKeys.user_by_username(username))
        if not cached_id:
            return None

        try:
            user = await self._repo.get_by_id(int(cached_id))
            if user:
                logger.debug("Cache HIT: username=%s", username)
                return user
        except ValueError:
            pass

        return None

    async def _cache_username_mapping(self, username: str, user_id: int) -> None:
        """Store username→ID mapping in cache."""
        if not self._cache:
            return
        await self._cache.set(
            CacheKeys.user_by_username(username),
            str(user_id),
            PROFILE_CACHE_TTL,
        )
        logger.debug("Cache SET: username=%s → id=%d", username, user_id)

    # =========================================================================
    # Profile Caching
    # =========================================================================

    async def get_user_profile_cached(self, user_id: int) -> UserProfile | None:
        """Retrieve cached user profile, or None if not cached."""
        if not self._cache:
            return None
        return await self._cache.get_json(CacheKeys.user(user_id))

    async def cache_user_profile(self, user: User) -> None:
        """Store user profile and username mapping in cache."""
        if not self._cache:
            return
        profile = self._build_profile(user)
        await self._cache.set_json(CacheKeys.user(user.id), profile, PROFILE_CACHE_TTL)
        await self._cache_username_mapping(user.username, user.id)

    @staticmethod
    def _build_profile(user: User) -> UserProfile:
        """Build cacheable profile dictionary from user model."""
        return UserProfile(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            bio=user.bio,
            avatar_url=user.avatar_url,
            location=user.location,
            website=user.website,
            followers_count=user.followers_count,
            following_count=user.following_count,
            posts_count=user.posts_count,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat() if user.created_at else None,
        )

    # =========================================================================
    # Profile Management
    # =========================================================================

    async def update_profile(self, user_id: int, data: UserUpdate) -> User:
        """
        Update user profile fields.

        Raises:
            UserNotFoundError: User does not exist.
            UsernameConflictError: Username already taken.
        """
        current_user = await self._repo.get_by_id(user_id)
        old_username = current_user.username if current_user else None

        await self._ensure_username_available(user_id, data.username)

        user = await self._repo.update(user_id, **data.model_dump(exclude_unset=True))
        if not user:
            raise UserNotFoundError()

        await self._invalidate_user_caches(user_id, old_username, data.username)
        logger.info("Profile updated: user_id=%d", user_id)
        return user

    async def _ensure_username_available(
        self, user_id: int, new_username: str | None
    ) -> None:
        """Validate username is available for this user."""
        if not new_username:
            return
        existing = await self._repo.get_by_username(new_username)
        if existing and existing.id != user_id:
            raise UsernameConflictError()

    async def _invalidate_user_caches(
        self,
        user_id: int,
        old_username: str | None,
        new_username: str | None,
    ) -> None:
        """Invalidate all cache entries for user."""
        if not self._invalidator:
            return
        await self._invalidator.invalidate_user(user_id, old_username)
        if new_username and new_username != old_username:
            await self._invalidator.invalidate_user(user_id, new_username)

    async def update_password(self, user_id: int, data: UserPasswordUpdate) -> None:
        """
        Change user password after verifying current password.

        Raises:
            UserNotFoundError: User does not exist.
            PasswordMismatchError: Current password incorrect.
        """
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        if not verify_password(data.current_password, user.password_hash):
            raise PasswordMismatchError()

        await self._repo.update(user_id, password_hash=hash_password(data.new_password))
        logger.info("Password updated: user_id=%d", user_id)

    # =========================================================================
    # Avatar Management
    # =========================================================================

    async def upload_avatar(self, user_id: int, file: UploadFile) -> str:
        """
        Upload new avatar, replacing any existing one.

        Returns:
            URL of the uploaded avatar.

        Raises:
            UserNotFoundError: User does not exist.
            InvalidAvatarTypeError: Invalid file type.
            AvatarTooLargeError: File exceeds size limit.
        """
        user = await self.get_user_by_id(user_id)
        avatar_url = await self._avatar.replace(user_id, file, user.avatar_url)
        await self._repo.update(user_id, avatar_url=avatar_url)
        logger.info("Avatar uploaded: user_id=%d", user_id)
        return avatar_url

    async def delete_avatar(self, user_id: int) -> None:
        """
        Remove user's avatar, reverting to default.

        Raises:
            UserNotFoundError: User does not exist.
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
        Create follow relationship.

        Returns:
            True if follow created, False if already following.

        Raises:
            CannotFollowSelfError: Attempted self-follow.
            UserNotFoundError: Target user does not exist.
        """
        self._assert_not_self_follow(follower_id, followed_id)
        await self._assert_user_exists(followed_id)

        if not await self._repo.follow(follower_id, followed_id):
            return False

        logger.info("Follow created: %d → %d", follower_id, followed_id)
        await self._handle_follow_created(follower_id, followed_id)
        return True

    async def unfollow_user(self, follower_id: int, followed_id: int) -> bool:
        """
        Remove follow relationship.

        Returns:
            True if unfollowed, False if wasn't following.
        """
        if not await self._repo.unfollow(follower_id, followed_id):
            return False

        logger.info("Follow removed: %d → %d", follower_id, followed_id)
        if self._invalidator:
            await self._invalidator.on_unfollow(follower_id, followed_id)
        return True

    async def is_following(self, follower_id: int, followed_id: int) -> bool:
        """Check if follower_id follows followed_id."""
        return await self._repo.is_following(follower_id, followed_id)

    @staticmethod
    def _assert_not_self_follow(follower_id: int, followed_id: int) -> None:
        """Guard against self-follow attempts."""
        if follower_id == followed_id:
            raise CannotFollowSelfError()

    async def _assert_user_exists(self, user_id: int) -> None:
        """Guard against operations on non-existent users."""
        if not await self._repo.get_by_id(user_id):
            raise UserNotFoundError()

    async def _handle_follow_created(
        self, follower_id: int, followed_id: int
    ) -> None:
        """Process side effects of new follow relationship."""
        if self._invalidator:
            await self._invalidator.on_follow(follower_id, followed_id)
        await self._notify_new_follower(follower_id, followed_id)

    async def _notify_new_follower(
        self, follower_id: int, followed_id: int
    ) -> None:
        """Send follow notification if service available."""
        if not self._notifications:
            return
        follower = await self._repo.get_by_id(follower_id)
        if follower:
            await self._notifications.notify_new_follower(
                user_id=followed_id,
                follower_id=follower_id,
                follower_username=follower.username,
            )

    # =========================================================================
    # Counts
    # =========================================================================

    async def get_followers_count(self, user_id: int) -> int:
        """Get user's follower count (cached)."""
        return await self._get_count(user_id, _CountType.FOLLOWERS)

    async def get_following_count(self, user_id: int) -> int:
        """Get user's following count (cached)."""
        return await self._get_count(user_id, _CountType.FOLLOWING)

    async def _get_count(self, user_id: int, count_type: _CountType) -> int:
        """
        Retrieve count with cache-aside pattern.

        Falls back to database on cache miss and warms cache.
        """
        cache_key = self._count_cache_key(user_id, count_type)

        if self._cache:
            cached = await self._cache.get_counter(cache_key)
            if cached is not None:
                return cached

        user = await self._repo.get_by_id(user_id)
        count = getattr(user, count_type.value, 0) if user else 0

        if self._cache and user:
            await self._cache.set_counter(cache_key, count, COUNTS_CACHE_TTL)

        return count

    @staticmethod
    def _count_cache_key(user_id: int, count_type: _CountType) -> str:
        """Build cache key for count type."""
        if count_type == _CountType.FOLLOWERS:
            return CacheKeys.user_followers_count(user_id)
        return CacheKeys.user_following_count(user_id)

    # =========================================================================
    # Follower/Following Lists
    # =========================================================================

    async def get_followers(
        self, user_id: int, *, page: int = 1, per_page: int = 20
    ) -> PaginatedResult[User]:
        """Get paginated list of user's followers."""
        skip = calculate_skip(page, per_page)
        users, total = await self._repo.get_followers_paginated(
            user_id, skip=skip, limit=per_page
        )
        return PaginatedResult.create(list(users), total, page, per_page)

    async def get_following(
        self, user_id: int, *, page: int = 1, per_page: int = 20
    ) -> PaginatedResult[User]:
        """Get paginated list of users being followed."""
        skip = calculate_skip(page, per_page)
        users, total = await self._repo.get_following_paginated(
            user_id, skip=skip, limit=per_page
        )
        return PaginatedResult.create(list(users), total, page, per_page)

    # =========================================================================
    # User Discovery
    # =========================================================================

    async def search_users(
        self, query: str, *, page: int = 1, per_page: int = 20
    ) -> PaginatedResult[User]:
        """Search users by username or display name."""
        skip = calculate_skip(page, per_page)
        users, total = await self._repo.search_users(query, skip=skip, limit=per_page)
        return PaginatedResult.create(list(users), total, page, per_page)

    async def get_suggested_users(self, user_id: int, *, limit: int = 10) -> list[User]:
        """
        Get suggested users to follow.

        Returns popular users not already followed by this user.
        """
        following_ids = await self._repo.get_following_ids(user_id)
        exclude_ids = {user_id, *following_ids}
        suggestions = await self._repo.get_popular_users(
            exclude_ids=exclude_ids, limit=limit
        )
        return list(suggestions)


# =============================================================================
# Backward Compatibility Exports
# =============================================================================
# Re-exported for existing code that imports from this module.
# New code should import directly from the canonical locations.

from app.services.avatar_service import AvatarConfig  # noqa: E402, F401
from app.services.exceptions import (  # noqa: E402, F401
    CannotFollowSelfError as CannotFollowSelfError,
    InvalidAvatarError as InvalidAvatarError,
    PasswordMismatchError as PasswordMismatchError,
    UserNotFoundError as UserNotFoundError,
    UsernameConflictError as UsernameConflictError,
)
from app.services.storage import (  # noqa: E402, F401
    FileStorage as FileStorage,
    LocalFileStorage as LocalFileStorage,
)
