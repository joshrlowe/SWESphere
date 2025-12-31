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
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

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
    from collections.abc import Callable, Coroutine
    from typing import Any

    from fastapi import UploadFile

    from app.models.user import User
    from app.services.cache_invalidation import CacheInvalidator
    from app.services.cache_service import CacheService
    from app.services.notification_service import NotificationService

    # Type for paginated repository queries
    PaginatedRepoQuery = Callable[
        [int, int], Coroutine[Any, Any, tuple[list[Any], int]]
    ]


logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

PROFILE_CACHE_TTL_SECONDS = 300  # 5 minutes
COUNTS_CACHE_TTL_SECONDS = 3600  # 1 hour

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
DEFAULT_SUGGESTIONS_LIMIT = 10


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


@dataclass(frozen=True, slots=True)
class CountCacheConfig:
    """Configuration for user count cache operations."""

    attribute_name: str
    cache_key_fn: Callable[[int], str]


# Count type to cache configuration mapping
_COUNT_CONFIGS: dict[str, CountCacheConfig] = {
    "followers": CountCacheConfig(
        attribute_name="followers_count",
        cache_key_fn=CacheKeys.user_followers_count,
    ),
    "following": CountCacheConfig(
        attribute_name="following_count",
        cache_key_fn=CacheKeys.user_following_count,
    ),
}


# =============================================================================
# Service
# =============================================================================


class UserService:
    """
    Orchestrates user operations with caching and notifications.

    Uses dependency injection for all collaborators, enabling testing
    and graceful degradation when optional services are unavailable.

    Args:
        user_repo: Repository for user database operations
        notification_service: Optional service for sending notifications
        avatar_service: Optional service for avatar file operations
        cache: Optional cache service for Redis operations
        cache_invalidator: Optional service for cache invalidation
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
    # Properties (backward compatibility - prefer direct injection)
    # -------------------------------------------------------------------------

    @property
    def user_repo(self) -> UserRepository:
        """Repository accessor (prefer constructor injection in new code)."""
        return self._repo

    @property
    def notification_service(self) -> NotificationService | None:
        """Notification service accessor (prefer constructor injection)."""
        return self._notifications

    # =========================================================================
    # User Retrieval
    # =========================================================================

    async def get_user_by_id(self, user_id: int) -> User:
        """
        Retrieve user by ID.

        Args:
            user_id: The user's unique identifier

        Returns:
            The User model instance

        Raises:
            UserNotFoundError: User does not exist
        """
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        return user

    async def get_user_by_username(self, username: str) -> User:
        """
        Retrieve user by username with cache optimization.

        Attempts to resolve username via cached ID mapping first,
        falling back to database lookup on cache miss.

        Args:
            username: The username to look up

        Returns:
            The User model instance

        Raises:
            UserNotFoundError: User does not exist
        """
        if cached_user := await self._try_resolve_from_cache(username):
            return cached_user

        user = await self._repo.get_by_username(username)
        if not user:
            raise UserNotFoundError()

        await self._cache_username_mapping(username, user.id)
        return user

    async def _try_resolve_from_cache(self, username: str) -> User | None:
        """
        Attempt to resolve user via cached username-to-ID mapping.

        Returns None on cache miss or if cache is unavailable.
        """
        if not self._cache:
            return None

        cached_id = await self._cache.get(CacheKeys.user_by_username(username))
        if not cached_id:
            return None

        try:
            user_id = int(cached_id)
        except ValueError:
            logger.warning(
                "Invalid cached user ID for username=%s: %r",
                username,
                cached_id,
            )
            return None

        user = await self._repo.get_by_id(user_id)
        if user:
            logger.debug("Cache hit for username=%s (user_id=%d)", username, user_id)
        return user

    async def _cache_username_mapping(self, username: str, user_id: int) -> None:
        """Store username-to-ID mapping in cache."""
        if not self._cache:
            return

        cache_key = CacheKeys.user_by_username(username)
        await self._cache.set(cache_key, str(user_id), PROFILE_CACHE_TTL_SECONDS)
        logger.debug("Cached username mapping: %s → %d", username, user_id)

    # =========================================================================
    # Profile Caching
    # =========================================================================

    async def get_user_profile_cached(self, user_id: int) -> UserProfile | None:
        """
        Retrieve cached user profile.

        Args:
            user_id: The user's unique identifier

        Returns:
            Cached profile dict or None if not cached
        """
        if not self._cache:
            return None
        return await self._cache.get_json(CacheKeys.user(user_id))

    async def cache_user_profile(self, user: User) -> None:
        """
        Store user profile and username mapping in cache.

        Args:
            user: The User model to cache
        """
        if not self._cache:
            return

        profile = self._serialize_profile(user)
        cache_key = CacheKeys.user(user.id)
        await self._cache.set_json(cache_key, profile, PROFILE_CACHE_TTL_SECONDS)
        await self._cache_username_mapping(user.username, user.id)

    @staticmethod
    def _serialize_profile(user: User) -> UserProfile:
        """
        Serialize User model to cacheable profile dictionary.

        Args:
            user: The User model instance

        Returns:
            UserProfile TypedDict suitable for JSON serialization
        """
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

        Args:
            user_id: The user's unique identifier
            data: Profile update data

        Returns:
            Updated User model

        Raises:
            UserNotFoundError: User does not exist
            UsernameConflictError: Username already taken by another user
        """
        current_user = await self._repo.get_by_id(user_id)
        old_username = current_user.username if current_user else None

        await self._validate_username_available(user_id, data.username)

        updated_user = await self._repo.update(
            user_id, **data.model_dump(exclude_unset=True)
        )
        if not updated_user:
            raise UserNotFoundError()

        await self._invalidate_user_caches(user_id, old_username, data.username)
        logger.info("Profile updated: user_id=%d", user_id)
        return updated_user

    async def _validate_username_available(
        self,
        user_id: int,
        new_username: str | None,
    ) -> None:
        """
        Validate that username is available for this user.

        Raises UsernameConflictError if taken by another user.
        """
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
        """Invalidate all cache entries for user after profile update."""
        if not self._invalidator:
            return

        await self._invalidator.invalidate_user(user_id, old_username)

        username_changed = new_username and new_username != old_username
        if username_changed:
            await self._invalidator.invalidate_user(user_id, new_username)

    async def update_password(self, user_id: int, data: UserPasswordUpdate) -> None:
        """
        Change user password after verifying current password.

        Args:
            user_id: The user's unique identifier
            data: Password update data with current and new passwords

        Raises:
            UserNotFoundError: User does not exist
            PasswordMismatchError: Current password is incorrect
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
    # Avatar Management
    # =========================================================================

    async def upload_avatar(self, user_id: int, file: UploadFile) -> str:
        """
        Upload new avatar, replacing any existing one.

        Args:
            user_id: The user's unique identifier
            file: Uploaded avatar file

        Returns:
            URL of the uploaded avatar

        Raises:
            UserNotFoundError: User does not exist
            InvalidAvatarTypeError: Invalid file type
            AvatarTooLargeError: File exceeds size limit
        """
        user = await self.get_user_by_id(user_id)
        avatar_url = await self._avatar.replace(user_id, file, user.avatar_url)
        await self._repo.update(user_id, avatar_url=avatar_url)
        logger.info("Avatar uploaded: user_id=%d", user_id)
        return avatar_url

    async def delete_avatar(self, user_id: int) -> None:
        """
        Remove user's avatar, reverting to default.

        Args:
            user_id: The user's unique identifier

        Raises:
            UserNotFoundError: User does not exist
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

        Args:
            follower_id: ID of the user who wants to follow
            followed_id: ID of the user to be followed

        Returns:
            True if follow created, False if already following

        Raises:
            CannotFollowSelfError: Attempted to follow self
            UserNotFoundError: Target user does not exist
        """
        self._validate_not_self_follow(follower_id, followed_id)
        await self._validate_user_exists(followed_id)

        if not await self._repo.follow(follower_id, followed_id):
            return False

        logger.info("Follow created: %d → %d", follower_id, followed_id)
        await self._on_follow_created(follower_id, followed_id)
        return True

    async def unfollow_user(self, follower_id: int, followed_id: int) -> bool:
        """
        Remove follow relationship.

        Args:
            follower_id: ID of the user who wants to unfollow
            followed_id: ID of the user to be unfollowed

        Returns:
            True if unfollowed, False if wasn't following
        """
        if not await self._repo.unfollow(follower_id, followed_id):
            return False

        logger.info("Follow removed: %d → %d", follower_id, followed_id)
        await self._on_follow_removed(follower_id, followed_id)
        return True

    async def is_following(self, follower_id: int, followed_id: int) -> bool:
        """
        Check if one user follows another.

        Args:
            follower_id: Potential follower's user ID
            followed_id: Potential followed user's ID

        Returns:
            True if follower_id follows followed_id
        """
        return await self._repo.is_following(follower_id, followed_id)

    @staticmethod
    def _validate_not_self_follow(follower_id: int, followed_id: int) -> None:
        """Raise CannotFollowSelfError if attempting self-follow."""
        if follower_id == followed_id:
            raise CannotFollowSelfError()

    async def _validate_user_exists(self, user_id: int) -> None:
        """Raise UserNotFoundError if user doesn't exist."""
        if not await self._repo.get_by_id(user_id):
            raise UserNotFoundError()

    async def _on_follow_created(self, follower_id: int, followed_id: int) -> None:
        """Handle side effects when a follow relationship is created."""
        if self._invalidator:
            await self._invalidator.on_follow(follower_id, followed_id)
        await self._send_follow_notification(follower_id, followed_id)

    async def _on_follow_removed(self, follower_id: int, followed_id: int) -> None:
        """Handle side effects when a follow relationship is removed."""
        if self._invalidator:
            await self._invalidator.on_unfollow(follower_id, followed_id)

    async def _send_follow_notification(
        self,
        follower_id: int,
        followed_id: int,
    ) -> None:
        """Send notification about new follower if service is available."""
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
    # Counts (with caching)
    # =========================================================================

    async def get_followers_count(self, user_id: int) -> int:
        """
        Get user's follower count with caching.

        Args:
            user_id: The user's unique identifier

        Returns:
            Number of followers
        """
        return await self._get_cached_count(user_id, "followers")

    async def get_following_count(self, user_id: int) -> int:
        """
        Get user's following count with caching.

        Args:
            user_id: The user's unique identifier

        Returns:
            Number of users being followed
        """
        return await self._get_cached_count(user_id, "following")

    async def _get_cached_count(self, user_id: int, count_type: str) -> int:
        """
        Retrieve count using cache-aside pattern.

        Falls back to database on cache miss and warms the cache.

        Args:
            user_id: The user's unique identifier
            count_type: One of "followers" or "following"

        Returns:
            The count value
        """
        config = _COUNT_CONFIGS[count_type]
        cache_key = config.cache_key_fn(user_id)

        # Try cache first
        if self._cache:
            cached_value = await self._cache.get_counter(cache_key)
            if cached_value is not None:
                return cached_value

        # Cache miss: fetch from database
        user = await self._repo.get_by_id(user_id)
        count = getattr(user, config.attribute_name, 0) if user else 0

        # Warm the cache
        if self._cache and user:
            await self._cache.set_counter(cache_key, count, COUNTS_CACHE_TTL_SECONDS)

        return count

    # =========================================================================
    # Follower/Following Lists
    # =========================================================================

    async def get_followers(
        self,
        user_id: int,
        *,
        page: int = DEFAULT_PAGE,
        per_page: int = DEFAULT_PAGE_SIZE,
    ) -> PaginatedResult[User]:
        """
        Get paginated list of user's followers.

        Args:
            user_id: The user whose followers to retrieve
            page: Page number (1-indexed)
            per_page: Number of items per page

        Returns:
            Paginated result containing follower User objects
        """
        return await self._get_paginated_users(
            user_id,
            self._repo.get_followers_paginated,
            page=page,
            per_page=per_page,
        )

    async def get_following(
        self,
        user_id: int,
        *,
        page: int = DEFAULT_PAGE,
        per_page: int = DEFAULT_PAGE_SIZE,
    ) -> PaginatedResult[User]:
        """
        Get paginated list of users being followed.

        Args:
            user_id: The user whose following list to retrieve
            page: Page number (1-indexed)
            per_page: Number of items per page

        Returns:
            Paginated result containing followed User objects
        """
        return await self._get_paginated_users(
            user_id,
            self._repo.get_following_paginated,
            page=page,
            per_page=per_page,
        )

    async def _get_paginated_users(
        self,
        user_id: int,
        repo_method: PaginatedRepoQuery,
        *,
        page: int,
        per_page: int,
    ) -> PaginatedResult[User]:
        """
        Execute a paginated user query.

        Encapsulates the common pattern of calculating skip,
        calling repository, and building the result.
        """
        skip = calculate_skip(page, per_page)
        users, total = await repo_method(user_id, skip=skip, limit=per_page)
        return PaginatedResult.create(list(users), total, page, per_page)

    # =========================================================================
    # User Discovery
    # =========================================================================

    async def search_users(
        self,
        query: str,
        *,
        page: int = DEFAULT_PAGE,
        per_page: int = DEFAULT_PAGE_SIZE,
    ) -> PaginatedResult[User]:
        """
        Search users by username or display name.

        Args:
            query: Search term
            page: Page number (1-indexed)
            per_page: Number of items per page

        Returns:
            Paginated result containing matching User objects
        """
        skip = calculate_skip(page, per_page)
        users, total = await self._repo.search_users(query, skip=skip, limit=per_page)
        return PaginatedResult.create(list(users), total, page, per_page)

    async def get_suggested_users(
        self,
        user_id: int,
        *,
        limit: int = DEFAULT_SUGGESTIONS_LIMIT,
    ) -> list[User]:
        """
        Get suggested users to follow.

        Returns popular users not already followed by this user.

        Args:
            user_id: The user to get suggestions for
            limit: Maximum number of suggestions

        Returns:
            List of suggested User objects
        """
        following_ids = await self._repo.get_following_ids(user_id)
        exclude_ids = {user_id, *following_ids}

        suggestions = await self._repo.get_popular_users(
            exclude_ids=exclude_ids,
            limit=limit,
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
