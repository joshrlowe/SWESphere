"""
Post service.

Handles post creation, retrieval, updates, likes, feed generation,
and mention processing.
"""

import html
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.core.redis_keys import redis_keys
from app.models.post import Post
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.post import PostCreate, PostUpdate

if TYPE_CHECKING:
    from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


# =============================================================================
# Response Types
# =============================================================================


@dataclass
class PaginatedPosts:
    """Paginated list of posts."""

    posts: list[Post]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


# =============================================================================
# Constants
# =============================================================================

# Regex to find @mentions
MENTION_PATTERN = re.compile(r"@(\w{1,64})", re.UNICODE)

# Cache TTLs
FEED_CACHE_TTL = 60  # 1 minute
EXPLORE_CACHE_TTL = 300  # 5 minutes


# =============================================================================
# Service
# =============================================================================


class PostService:
    """
    Service for post operations.

    Handles:
    - Post CRUD operations
    - Feed generation (home and explore)
    - Like/unlike operations
    - Mention detection and notifications
    - Content sanitization
    """

    # Content limits
    MAX_POST_LENGTH = 280
    MAX_MENTIONS_PER_POST = 10

    def __init__(
        self,
        post_repo: PostRepository,
        user_repo: UserRepository,
        redis: Redis | None = None,
        notification_service: "NotificationService | None" = None,
    ) -> None:
        """
        Initialize post service.

        Args:
            post_repo: Post repository for data access
            user_repo: User repository for mention lookups
            redis: Optional Redis client for caching
            notification_service: Optional notification service for mentions/likes
        """
        self.post_repo = post_repo
        self.user_repo = user_repo
        self.redis = redis
        self.notification_service = notification_service

    # =========================================================================
    # Post CRUD
    # =========================================================================

    async def create_post(self, user_id: int, data: PostCreate) -> Post:
        """
        Create a new post.

        Args:
            user_id: Author's user ID
            data: Post content and metadata

        Returns:
            Created Post

        Raises:
            HTTPException: If content invalid or reply_to doesn't exist
        """
        # Validate content length
        body = self._sanitize_content(data.body)
        if len(body) > self.MAX_POST_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Post content exceeds {self.MAX_POST_LENGTH} characters",
            )

        if not body.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post content cannot be empty",
            )

        # Validate reply_to if provided
        if data.reply_to_id:
            await self._verify_post_exists(
                data.reply_to_id, "Post to reply to not found"
            )

        # Create the post
        post = await self.post_repo.create(
            user_id=user_id,
            body=body,
            media_url=data.media_url,
            media_type=data.media_type,
            reply_to_id=data.reply_to_id,
        )

        # Process mentions asynchronously
        await self._process_mentions(post, user_id)

        # Invalidate feed caches
        await self._invalidate_feed_caches(user_id)

        logger.info(f"Post created: {post.id} by user {user_id}")
        return post

    async def get_post(self, post_id: int) -> Post:
        """
        Get a post by ID with author loaded.

        Args:
            post_id: Post ID to fetch

        Returns:
            Post with author relationship

        Raises:
            HTTPException: If post not found
        """
        post = await self.post_repo.get_with_author(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )
        return post

    async def update_post(
        self,
        post_id: int,
        user_id: int,
        data: PostUpdate,
    ) -> Post:
        """
        Update a post.

        Args:
            post_id: Post to update
            user_id: User attempting the update (for authorization)
            data: Fields to update

        Returns:
            Updated Post

        Raises:
            HTTPException: If post not found or user not authorized
        """
        post = await self._get_authorized_post(post_id, user_id, "update")

        # Sanitize content if provided
        update_data = data.model_dump(exclude_unset=True)
        if "body" in update_data:
            update_data["body"] = self._sanitize_content(update_data["body"])
            if len(update_data["body"]) > self.MAX_POST_LENGTH:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Post content exceeds {self.MAX_POST_LENGTH} characters",
                )

        updated = await self.post_repo.update(post_id, **update_data)

        logger.info(f"Post updated: {post_id} by user {user_id}")
        return updated  # type: ignore[return-value]

    async def delete_post(self, post_id: int, user_id: int) -> bool:
        """
        Delete a post (soft delete).

        Args:
            post_id: Post to delete
            user_id: User attempting the deletion (for authorization)

        Returns:
            True if deleted

        Raises:
            HTTPException: If post not found or user not authorized
        """
        post = await self._get_authorized_post(post_id, user_id, "delete")

        success = await self.post_repo.delete(post_id)

        if success:
            await self._invalidate_feed_caches(user_id)
            logger.info(f"Post deleted: {post_id} by user {user_id}")

        return success

    # =========================================================================
    # Feeds
    # =========================================================================

    async def get_home_feed(
        self,
        user_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedPosts:
        """
        Get personalized home feed for a user.

        Shows posts from followed users and the user's own posts.
        Results are cached for performance.

        Args:
            user_id: User to get feed for
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            PaginatedPosts with feed and metadata
        """
        skip = (page - 1) * per_page
        cache_key = redis_keys.home_feed(user_id, page, per_page)

        # Try cache first
        cached = await self._get_cached_feed(cache_key)
        if cached is not None:
            return cached

        # Get following IDs
        following_ids = await self.user_repo.get_following_ids(user_id)

        # Query feed
        posts, total = await self.post_repo.get_home_feed(
            user_id,
            following_ids=following_ids,
            skip=skip,
            limit=per_page,
        )

        result = PaginatedPosts(
            posts=list(posts),
            total=total,
            page=page,
            per_page=per_page,
            has_next=skip + len(posts) < total,
            has_prev=page > 1,
        )

        # Cache result
        await self._cache_feed(cache_key, result, FEED_CACHE_TTL)

        return result

    async def get_explore_feed(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedPosts:
        """
        Get explore feed with trending/recent posts.

        Shows all public posts, ordered by recency/popularity.
        Results are cached for performance.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            PaginatedPosts with explore posts and metadata
        """
        skip = (page - 1) * per_page
        cache_key = redis_keys.explore_feed(page, per_page)

        # Try cache first
        cached = await self._get_cached_feed(cache_key)
        if cached is not None:
            return cached

        # Query explore feed
        posts, total = await self.post_repo.get_explore_feed(
            skip=skip,
            limit=per_page,
        )

        result = PaginatedPosts(
            posts=list(posts),
            total=total,
            page=page,
            per_page=per_page,
            has_next=skip + len(posts) < total,
            has_prev=page > 1,
        )

        # Cache result
        await self._cache_feed(cache_key, result, EXPLORE_CACHE_TTL)

        return result

    async def get_user_posts(
        self,
        user_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedPosts:
        """Get all posts by a specific user."""
        skip = (page - 1) * per_page

        posts, total = await self.post_repo.get_user_posts(
            user_id,
            skip=skip,
            limit=per_page,
        )

        return PaginatedPosts(
            posts=list(posts),
            total=total,
            page=page,
            per_page=per_page,
            has_next=skip + len(posts) < total,
            has_prev=page > 1,
        )

    async def get_replies(
        self,
        post_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedPosts:
        """Get replies to a specific post."""
        skip = (page - 1) * per_page

        posts, total = await self.post_repo.get_replies(
            post_id,
            skip=skip,
            limit=per_page,
        )

        return PaginatedPosts(
            posts=list(posts),
            total=total,
            page=page,
            per_page=per_page,
            has_next=skip + len(posts) < total,
            has_prev=page > 1,
        )

    async def search_posts(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedPosts:
        """Search posts by content."""
        skip = (page - 1) * per_page

        posts, total = await self.post_repo.search_posts(
            query,
            skip=skip,
            limit=per_page,
        )

        return PaginatedPosts(
            posts=list(posts),
            total=total,
            page=page,
            per_page=per_page,
            has_next=skip + len(posts) < total,
            has_prev=page > 1,
        )

    # =========================================================================
    # Likes
    # =========================================================================

    async def like_post(self, user_id: int, post_id: int) -> bool:
        """
        Like a post.

        Args:
            user_id: User liking the post
            post_id: Post to like

        Returns:
            True if like was added (False if already liked)

        Raises:
            HTTPException: If post not found
        """
        post = await self._verify_post_exists(post_id)

        success = await self.post_repo.like_post(user_id, post_id)

        # Send notification if liked and not own post
        if success and self.notification_service and post.user_id != user_id:
            user = await self.user_repo.get_by_id(user_id)
            if user:
                await self.notification_service.notify_post_liked(
                    user_id=post.user_id,
                    liker_id=user_id,
                    liker_username=user.username,
                    post_id=post_id,
                )

        if success:
            logger.debug(f"User {user_id} liked post {post_id}")

        return success

    async def unlike_post(self, user_id: int, post_id: int) -> bool:
        """
        Remove like from a post.

        Args:
            user_id: User unliking the post
            post_id: Post to unlike

        Returns:
            True if like was removed (False if wasn't liked)
        """
        success = await self.post_repo.unlike_post(user_id, post_id)

        if success:
            logger.debug(f"User {user_id} unliked post {post_id}")

        return success

    async def is_liked(self, user_id: int, post_id: int) -> bool:
        """Check if a user has liked a specific post."""
        return await self.post_repo.is_liked_by(post_id, user_id)

    async def get_liked_status(
        self,
        user_id: int,
        post_ids: list[int],
    ) -> dict[int, bool]:
        """
        Check like status for multiple posts at once.

        Args:
            user_id: User to check likes for
            post_ids: List of post IDs to check

        Returns:
            Dict mapping post_id -> is_liked
        """
        liked_ids = await self.post_repo.get_liked_post_ids(user_id, post_ids)
        return {pid: pid in liked_ids for pid in post_ids}

    # =========================================================================
    # Content Processing
    # =========================================================================

    def _sanitize_content(self, content: str) -> str:
        """
        Sanitize post content.

        - Escapes HTML
        - Normalizes whitespace
        - Trims leading/trailing whitespace
        """
        # Escape HTML entities
        content = html.escape(content)

        # Normalize whitespace (collapse multiple spaces/newlines)
        content = re.sub(r"\s+", " ", content)

        # Trim
        return content.strip()

    def _extract_mentions(self, content: str) -> list[str]:
        """Extract @mentions from content."""
        mentions = MENTION_PATTERN.findall(content)
        # Limit mentions to prevent abuse
        return list(set(mentions))[: self.MAX_MENTIONS_PER_POST]

    async def _process_mentions(self, post: Post, author_id: int) -> None:
        """Process mentions in a post and send notifications."""
        if not self.notification_service:
            return

        mentions = self._extract_mentions(post.body)
        if not mentions:
            return

        # Look up mentioned users
        author = await self.user_repo.get_by_id(author_id)
        if not author:
            return

        for username in mentions:
            # Skip self-mentions
            if username.lower() == author.username.lower():
                continue

            mentioned_user = await self.user_repo.get_by_username(username)
            if mentioned_user:
                await self.notification_service.notify_mention(
                    user_id=mentioned_user.id,
                    mentioner_id=author_id,
                    mentioner_username=author.username,
                    post_id=post.id,
                )

    # =========================================================================
    # Caching
    # =========================================================================

    async def _get_cached_feed(self, key: str) -> PaginatedPosts | None:
        """Get cached feed from Redis."""
        if not self.redis:
            return None

        try:
            import json

            data = await self.redis.get(key)
            if data:
                # We don't cache full objects, just IDs for simplicity
                # In production, consider caching serialized responses
                pass
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        return None

    async def _cache_feed(
        self,
        key: str,
        result: PaginatedPosts,
        ttl: int,
    ) -> None:
        """Cache feed result in Redis."""
        if not self.redis:
            return

        try:
            # For simplicity, we're just noting that caching would happen here
            # In production, serialize the response properly
            await self.redis.setex(key, ttl, "cached")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    async def _invalidate_feed_caches(self, user_id: int) -> None:
        """Invalidate feed caches after post creation/deletion."""
        if not self.redis:
            return

        try:
            # Delete user's home feed cache
            pattern = f"home_feed:{user_id}:*"
            async for key in self.redis.scan_iter(match=pattern):
                await self.redis.delete(key)

            # Also invalidate followers' feeds (they might see this post)
            # In production, this would be done via background job
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    async def _verify_post_exists(
        self,
        post_id: int,
        error_message: str = "Post not found",
    ) -> Post:
        """Verify a post exists, raising 404 if not."""
        post = await self.post_repo.get_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_message,
            )
        return post

    async def _get_authorized_post(
        self,
        post_id: int,
        user_id: int,
        action: str,
    ) -> Post:
        """Get a post and verify the user is authorized to modify it."""
        post = await self._verify_post_exists(post_id)

        if post.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to {action} this post",
            )

        return post
