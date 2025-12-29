"""
Cache invalidation service.

Handles cache invalidation strategies for:
- User profile updates
- Post creation/updates/deletion
- Feed invalidation
- Follow/unfollow events

Follows the "invalidate on write" pattern for cache consistency.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.redis_keys import CacheKeys

if TYPE_CHECKING:
    from app.models.post import Post
    from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class CacheInvalidator:
    """
    Cache invalidation coordinator.

    Provides high-level invalidation operations that handle
    cascading invalidation across related cache entries.

    Strategies:
    - User updates: Invalidate profile + username lookup
    - Post updates: Invalidate post + author feeds + explore feed
    - New post: Prepend to feeds (fanout on write) or invalidate feeds
    - Follow/unfollow: Invalidate feed + update counters
    """

    def __init__(self, cache: "CacheService") -> None:
        """
        Initialize cache invalidator.

        Args:
            cache: CacheService instance for cache operations
        """
        self._cache = cache

    # =========================================================================
    # User Invalidation
    # =========================================================================

    async def invalidate_user(
        self,
        user_id: int,
        username: str | None = None,
    ) -> None:
        """
        Invalidate all cached data for a user.

        Clears:
        - User profile cache
        - Username-to-ID lookup (if username provided)

        Args:
            user_id: User ID to invalidate
            username: Optional username to also invalidate lookup
        """
        # Delete profile cache
        await self._cache.delete(CacheKeys.user(user_id))

        # Delete username lookup if provided
        if username:
            await self._cache.delete(CacheKeys.user_by_username(username))

        logger.debug(f"Invalidated user cache: user_id={user_id}")

    async def invalidate_user_feeds(self, user_id: int) -> None:
        """
        Invalidate all feed caches for a user.

        Clears all paginated home feed caches for the user.

        Args:
            user_id: User whose feeds to invalidate
        """
        pattern = CacheKeys.home_feed_pattern(user_id)
        deleted = await self._cache.delete_pattern(pattern)
        logger.debug(f"Invalidated {deleted} feed cache entries for user {user_id}")

    async def invalidate_followers_feeds(
        self,
        user_id: int,
        follower_ids: list[int],
    ) -> None:
        """
        Invalidate home feeds for all of a user's followers.

        Used when a user creates a new post - all followers need
        their home feeds invalidated or updated.

        Args:
            user_id: User whose followers to update
            follower_ids: List of follower user IDs
        """
        for follower_id in follower_ids:
            await self.invalidate_user_feeds(follower_id)

        logger.debug(
            f"Invalidated feeds for {len(follower_ids)} followers of user {user_id}"
        )

    # =========================================================================
    # Post Invalidation
    # =========================================================================

    async def invalidate_post(self, post_id: int) -> None:
        """
        Invalidate cached post data.

        Clears:
        - Post cache
        - (Note: Like counts are write-through, not invalidated)

        Args:
            post_id: Post ID to invalidate
        """
        await self._cache.delete(CacheKeys.post(post_id))
        logger.debug(f"Invalidated post cache: post_id={post_id}")

    async def invalidate_explore_feed(self) -> None:
        """
        Invalidate all explore feed caches.

        Used when trending/popular content changes.
        """
        pattern = CacheKeys.explore_feed_pattern()
        deleted = await self._cache.delete_pattern(pattern)
        logger.debug(f"Invalidated {deleted} explore feed cache entries")

    # =========================================================================
    # Event Handlers
    # =========================================================================

    async def on_new_post(
        self,
        post: "Post",
        author_id: int,
        follower_ids: list[int],
    ) -> None:
        """
        Handle cache updates when a new post is created.

        Strategy: Invalidate feeds (simpler than fanout-on-write).
        For high-traffic apps, consider prepending to cached feeds instead.

        Args:
            post: The newly created post
            author_id: ID of the post author
            follower_ids: IDs of users following the author
        """
        # Invalidate author's own feed (they see their own posts)
        await self.invalidate_user_feeds(author_id)

        # Invalidate all followers' feeds
        await self.invalidate_followers_feeds(author_id, follower_ids)

        # Invalidate explore feed (new content affects trending)
        await self.invalidate_explore_feed()

        logger.info(
            f"Cache invalidated for new post {post.id} by user {author_id}"
        )

    async def on_post_update(self, post_id: int) -> None:
        """
        Handle cache updates when a post is updated.

        Args:
            post_id: ID of the updated post
        """
        await self.invalidate_post(post_id)
        logger.debug(f"Cache invalidated for updated post {post_id}")

    async def on_post_delete(
        self,
        post_id: int,
        author_id: int,
        follower_ids: list[int],
    ) -> None:
        """
        Handle cache updates when a post is deleted.

        Args:
            post_id: ID of the deleted post
            author_id: ID of the post author
            follower_ids: IDs of users following the author
        """
        # Invalidate the post itself
        await self.invalidate_post(post_id)

        # Invalidate author's feed
        await self.invalidate_user_feeds(author_id)

        # Invalidate followers' feeds
        await self.invalidate_followers_feeds(author_id, follower_ids)

        # Invalidate explore feed
        await self.invalidate_explore_feed()

        # Clean up like tracking
        await self._cache.delete(CacheKeys.post_likers(post_id))
        await self._cache.delete(CacheKeys.post_likes_count(post_id))

        logger.info(f"Cache invalidated for deleted post {post_id}")

    async def on_follow(
        self,
        follower_id: int,
        followed_id: int,
    ) -> None:
        """
        Handle cache updates when a user follows another.

        Updates:
        - Follower's home feed (now includes followed user's posts)
        - Both users' follower/following counts

        Args:
            follower_id: User who is following
            followed_id: User being followed
        """
        # Invalidate follower's home feed (they now see followed's posts)
        await self.invalidate_user_feeds(follower_id)

        # Update follower count for followed user
        await self._cache.incr(CacheKeys.user_followers_count(followed_id))

        # Update following count for follower
        await self._cache.incr(CacheKeys.user_following_count(follower_id))

        logger.debug(f"Cache updated: user {follower_id} followed user {followed_id}")

    async def on_unfollow(
        self,
        follower_id: int,
        followed_id: int,
    ) -> None:
        """
        Handle cache updates when a user unfollows another.

        Updates:
        - Follower's home feed (no longer includes unfollowed user's posts)
        - Both users' follower/following counts

        Args:
            follower_id: User who is unfollowing
            followed_id: User being unfollowed
        """
        # Invalidate follower's home feed
        await self.invalidate_user_feeds(follower_id)

        # Decrement follower count for unfollowed user
        await self._cache.decr(CacheKeys.user_followers_count(followed_id))

        # Decrement following count for follower
        await self._cache.decr(CacheKeys.user_following_count(follower_id))

        logger.debug(f"Cache updated: user {follower_id} unfollowed user {followed_id}")

    async def on_like(self, user_id: int, post_id: int) -> None:
        """
        Handle cache updates when a user likes a post.

        Uses write-through pattern for like counts.

        Args:
            user_id: User who liked
            post_id: Post that was liked
        """
        # Increment like counter (write-through)
        await self._cache.incr(CacheKeys.post_likes_count(post_id))

        # Track user in likers set (for quick "has liked" checks)
        await self._cache.add_to_set(
            CacheKeys.post_likers(post_id),
            str(user_id),
        )

        logger.debug(f"Cache updated: user {user_id} liked post {post_id}")

    async def on_unlike(self, user_id: int, post_id: int) -> None:
        """
        Handle cache updates when a user unlikes a post.

        Args:
            user_id: User who unliked
            post_id: Post that was unliked
        """
        # Decrement like counter
        await self._cache.decr(CacheKeys.post_likes_count(post_id))

        # Remove user from likers set
        await self._cache.remove_from_set(
            CacheKeys.post_likers(post_id),
            str(user_id),
        )

        logger.debug(f"Cache updated: user {user_id} unliked post {post_id}")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def clear_all_caches(self) -> bool:
        """
        Clear all caches (USE WITH CAUTION).

        Only for development/testing.

        Returns:
            True if successful
        """
        logger.warning("Clearing all caches!")
        return await self._cache.flush_all()

    async def warm_user_cache(
        self,
        user_id: int,
        profile_data: dict,
        username: str,
        ttl: int = 300,
    ) -> None:
        """
        Pre-warm cache for a user profile.

        Args:
            user_id: User ID
            profile_data: Serialized profile data
            username: User's username
            ttl: Cache TTL in seconds
        """
        await self._cache.set_json(CacheKeys.user(user_id), profile_data, ttl)
        await self._cache.set(
            CacheKeys.user_by_username(username),
            str(user_id),
            ttl,
        )

    async def warm_post_cache(
        self,
        post_id: int,
        post_data: dict,
        likes_count: int,
        ttl: int = 60,
    ) -> None:
        """
        Pre-warm cache for a post.

        Args:
            post_id: Post ID
            post_data: Serialized post data
            likes_count: Current like count
            ttl: Cache TTL in seconds
        """
        await self._cache.set_json(CacheKeys.post(post_id), post_data, ttl)
        await self._cache.set_counter(CacheKeys.post_likes_count(post_id), likes_count)

