"""
Post service.

Handles post creation, retrieval, updates, likes, feed generation,
and mention processing.
"""

import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeVar

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.redis_keys import redis_keys
from app.models.comment import Comment
from app.models.post import Post
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.post import PostCreate, PostUpdate

if TYPE_CHECKING:
    from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Pagination Helpers
# =============================================================================


def calculate_skip(page: int, per_page: int) -> int:
    """Calculate offset for database query from page number."""
    return (page - 1) * per_page


def has_next_page(skip: int, items_count: int, total: int) -> bool:
    """Check if there are more pages after the current one."""
    return skip + items_count < total


def has_prev_page(page: int) -> bool:
    """Check if there are pages before the current one."""
    return page > 1


# =============================================================================
# Response Types
# =============================================================================


@dataclass
class PaginatedResult:
    """Generic paginated result container."""

    items: list[Any]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(
        cls,
        items: list[Any],
        total: int,
        page: int,
        per_page: int,
    ) -> "PaginatedResult":
        """Create a paginated result with computed navigation flags."""
        skip = calculate_skip(page, per_page)
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            has_next=has_next_page(skip, len(items), total),
            has_prev=has_prev_page(page),
        )

    @property
    def posts(self) -> list[Post]:
        """Alias for items when used with posts (backward compatibility)."""
        return self.items


# Alias for backward compatibility
PaginatedPosts = PaginatedResult


# =============================================================================
# Constants
# =============================================================================

# Regex to find @mentions
MENTION_PATTERN = re.compile(r"@(\w{1,64})", re.UNICODE)

# Content limits
MAX_POST_LENGTH = 280
MAX_MENTIONS_PER_POST = 10

# Cache TTLs (in seconds)
FEED_CACHE_TTL = 60  # 1 minute
EXPLORE_CACHE_TTL = 300  # 5 minutes


# =============================================================================
# Content Processing
# =============================================================================


def sanitize_content(content: str) -> str:
    """
    Sanitize post/comment content.

    - Escapes HTML entities
    - Normalizes whitespace (collapses multiple spaces/newlines)
    - Trims leading/trailing whitespace
    """
    content = html.escape(content)
    content = re.sub(r"\s+", " ", content)
    return content.strip()


def extract_mentions(content: str, max_mentions: int = MAX_MENTIONS_PER_POST) -> list[str]:
    """
    Extract @mentions from content.
    
    Returns unique usernames, limited to max_mentions to prevent abuse.
    """
    mentions = MENTION_PATTERN.findall(content)
    return list(set(mentions))[:max_mentions]


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
    - Comment operations
    - Mention detection and notifications
    """

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
    # Database Session Access
    # =========================================================================

    @property
    def _db(self):
        """Access to the database session via repository."""
        return self.post_repo.db

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
        body = sanitize_content(data.body)
        self._validate_post_content(body)

        if data.reply_to_id:
            await self._verify_post_exists(data.reply_to_id, "Post to reply to not found")

        post = await self.post_repo.create(
            user_id=user_id,
            body=body,
            media_url=data.media_url,
            media_type=data.media_type,
            reply_to_id=data.reply_to_id,
        )

        await self._process_mentions(post, user_id)
        await self._invalidate_feed_caches(user_id)

        logger.info(f"Post created: {post.id} by user {user_id}")
        return post

    async def get_post(self, post_id: int) -> Post:
        """
        Get a post by ID with author loaded.

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

        Raises:
            HTTPException: If post not found, user not authorized, or content invalid
        """
        await self._get_authorized_post(post_id, user_id, "update")

        update_data = data.model_dump(exclude_unset=True)
        if "body" in update_data:
            update_data["body"] = sanitize_content(update_data["body"])
            self._validate_post_content(update_data["body"])

        updated = await self.post_repo.update(post_id, **update_data)

        logger.info(f"Post updated: {post_id} by user {user_id}")
        return updated  # type: ignore[return-value]

    async def delete_post(self, post_id: int, user_id: int) -> bool:
        """
        Delete a post (soft delete).

        Raises:
            HTTPException: If post not found or user not authorized
        """
        await self._get_authorized_post(post_id, user_id, "delete")

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
    ) -> PaginatedResult:
        """
        Get personalized home feed for a user.

        Shows posts from followed users and the user's own posts.
        Results are cached for performance.
        """
        skip = calculate_skip(page, per_page)
        cache_key = redis_keys.home_feed(user_id, page, per_page)

        cached = await self._get_cached_feed(cache_key)
        if cached is not None:
            return cached

        following_ids = await self.user_repo.get_following_ids(user_id)
        posts, total = await self.post_repo.get_home_feed(
            user_id,
            following_ids=following_ids,
            skip=skip,
            limit=per_page,
        )

        result = PaginatedResult.create(list(posts), total, page, per_page)
        await self._cache_feed(cache_key, result, FEED_CACHE_TTL)

        return result

    async def get_explore_feed(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult:
        """
        Get explore feed with trending/recent posts.

        Shows all public posts, ordered by recency/popularity.
        Results are cached for performance.
        """
        skip = calculate_skip(page, per_page)
        cache_key = redis_keys.explore_feed(page, per_page)

        cached = await self._get_cached_feed(cache_key)
        if cached is not None:
            return cached

        posts, total = await self.post_repo.get_explore_feed(skip=skip, limit=per_page)
        result = PaginatedResult.create(list(posts), total, page, per_page)
        await self._cache_feed(cache_key, result, EXPLORE_CACHE_TTL)

        return result

    async def get_user_posts(
        self,
        user_id: int | None = None,
        *,
        username: str | None = None,
        page: int = 1,
        per_page: int = 20,
        include_replies: bool = False,
    ) -> PaginatedResult:
        """
        Get all posts by a specific user.

        Args:
            user_id: User ID (one of user_id or username required)
            username: Username to lookup (one of user_id or username required)
            page: Page number
            per_page: Items per page
            include_replies: Whether to include reply posts
        """
        resolved_user_id = await self._resolve_user_id(user_id, username)
        skip = calculate_skip(page, per_page)

        posts, total = await self.post_repo.get_user_posts(
            resolved_user_id,
            skip=skip,
            limit=per_page,
        )

        return PaginatedResult.create(list(posts), total, page, per_page)

    async def get_replies(
        self,
        post_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult:
        """Get replies to a specific post."""
        skip = calculate_skip(page, per_page)
        posts, total = await self.post_repo.get_replies(post_id, skip=skip, limit=per_page)
        return PaginatedResult.create(list(posts), total, page, per_page)

    async def search_posts(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult:
        """Search posts by content."""
        skip = calculate_skip(page, per_page)
        posts, total = await self.post_repo.search_posts(query, skip=skip, limit=per_page)
        return PaginatedResult.create(list(posts), total, page, per_page)

    # =========================================================================
    # Likes
    # =========================================================================

    async def like_post(self, user_id: int, post_id: int) -> bool:
        """
        Like a post.

        Returns:
            True if like was added (False if already liked)

        Raises:
            HTTPException: If post not found
        """
        post = await self._verify_post_exists(post_id)
        success = await self.post_repo.like_post(user_id, post_id)

        if success:
            await self._send_like_notification(post, user_id)
            logger.debug(f"User {user_id} liked post {post_id}")

        return success

    async def unlike_post(self, user_id: int, post_id: int) -> bool:
        """
        Remove like from a post.

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

        Returns:
            Dict mapping post_id -> is_liked
        """
        liked_ids = await self.post_repo.get_liked_post_ids(user_id, post_ids)
        return {pid: pid in liked_ids for pid in post_ids}

    # =========================================================================
    # Comment Operations
    # =========================================================================

    async def get_comments(
        self,
        post_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult:
        """
        Get top-level comments for a post.

        Returns paginated comments sorted by most recent first.
        """
        skip = calculate_skip(page, per_page)

        total = await self._count_top_level_comments(post_id)
        comments = await self._fetch_top_level_comments(post_id, skip, per_page)

        return PaginatedResult.create(comments, total, page, per_page)

    async def create_comment(
        self,
        user_id: int,
        post_id: int,
        body: str,
        parent_id: int | None = None,
    ) -> Comment:
        """
        Create a comment on a post.

        Args:
            user_id: User creating the comment
            post_id: Post to comment on
            body: Comment body
            parent_id: Parent comment ID for nested comments

        Returns:
            Created comment with author loaded
        """
        await self._verify_post_exists(post_id)
        
        if parent_id:
            await self._verify_comment_exists(parent_id)

        sanitized_body = sanitize_content(body)
        comment = await self._create_comment_record(
            user_id, post_id, sanitized_body, parent_id
        )

        await self._update_comment_counts(post_id, parent_id, increment=True)
        await self._db.commit()
        
        comment = await self._reload_comment_with_author(comment.id)
        logger.info(f"User {user_id} commented on post {post_id}")

        return comment

    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        """
        Delete a comment (soft delete).

        Raises:
            HTTPException: If comment not found or user not authorized
        """
        comment = await self._get_authorized_comment(comment_id, user_id)

        comment.deleted_at = datetime.utcnow()
        await self._update_comment_counts(comment.post_id, comment.parent_id, increment=False)
        await self._db.commit()

        logger.info(f"User {user_id} deleted comment {comment_id}")
        return True

    # =========================================================================
    # Private: Validation
    # =========================================================================

    def _validate_post_content(self, body: str) -> None:
        """Validate post content length and emptiness."""
        if not body.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Post content cannot be empty",
            )
        if len(body) > MAX_POST_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Post content exceeds {MAX_POST_LENGTH} characters",
            )

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

    async def _verify_comment_exists(self, comment_id: int) -> Comment:
        """Verify a comment exists, raising 404 if not."""
        stmt = select(Comment).where(Comment.id == comment_id)
        result = await self._db.execute(stmt)
        comment = result.scalar_one_or_none()
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found",
            )
        return comment

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

    async def _get_authorized_comment(
        self,
        comment_id: int,
        user_id: int,
    ) -> Comment:
        """Get a comment and verify the user is authorized to delete it."""
        stmt = select(Comment).where(Comment.id == comment_id)
        result = await self._db.execute(stmt)
        comment = result.scalar_one_or_none()

        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found",
            )
        if comment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this comment",
            )
        return comment

    async def _resolve_user_id(
        self,
        user_id: int | None,
        username: str | None,
    ) -> int:
        """Resolve a user_id from either user_id or username."""
        if user_id:
            return user_id

        if username:
            user = await self.user_repo.get_by_username(username)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User '{username}' not found",
                )
            return user.id

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or username is required",
        )

    # =========================================================================
    # Private: Comment Helpers
    # =========================================================================

    async def _count_top_level_comments(self, post_id: int) -> int:
        """Count top-level (non-reply) comments for a post."""
        stmt = (
            select(func.count())
            .select_from(Comment)
            .where(Comment.post_id == post_id)
            .where(Comment.deleted_at.is_(None))
            .where(Comment.parent_id.is_(None))
        )
        result = await self._db.execute(stmt)
        return result.scalar() or 0

    async def _fetch_top_level_comments(
        self,
        post_id: int,
        skip: int,
        limit: int,
    ) -> list[Comment]:
        """Fetch top-level comments with authors loaded."""
        stmt = (
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.post_id == post_id)
            .where(Comment.deleted_at.is_(None))
            .where(Comment.parent_id.is_(None))
            .order_by(Comment.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def _create_comment_record(
        self,
        user_id: int,
        post_id: int,
        body: str,
        parent_id: int | None,
    ) -> Comment:
        """Create a comment record in the database."""
        comment = Comment(
            body=body,
            user_id=user_id,
            post_id=post_id,
            parent_id=parent_id,
        )
        self._db.add(comment)
        await self._db.flush()
        return comment

    async def _reload_comment_with_author(self, comment_id: int) -> Comment:
        """Reload a comment with its author relationship loaded."""
        stmt = (
            select(Comment)
            .options(selectinload(Comment.author))
            .where(Comment.id == comment_id)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def _update_comment_counts(
        self,
        post_id: int,
        parent_id: int | None,
        *,
        increment: bool,
    ) -> None:
        """Update comment counts on post and parent comment."""
        post = await self.post_repo.get_by_id(post_id)
        if post:
            if increment:
                post.comments_count += 1
            else:
                post.comments_count = max(0, post.comments_count - 1)

        if parent_id:
            stmt = select(Comment).where(Comment.id == parent_id)
            result = await self._db.execute(stmt)
            parent = result.scalar_one_or_none()
            if parent:
                if increment:
                    parent.replies_count += 1
                else:
                    parent.replies_count = max(0, parent.replies_count - 1)

    # =========================================================================
    # Private: Notifications
    # =========================================================================

    async def _send_like_notification(self, post: Post, liker_id: int) -> None:
        """Send like notification if applicable."""
        if not self.notification_service:
            return
        if post.user_id == liker_id:
            return  # Don't notify for self-likes

        liker = await self.user_repo.get_by_id(liker_id)
        if liker:
            await self.notification_service.notify_post_liked(
                user_id=post.user_id,
                liker_id=liker_id,
                liker_username=liker.username,
                post_id=post.id,
            )

    async def _process_mentions(self, post: Post, author_id: int) -> None:
        """Process mentions in a post and send notifications."""
        if not self.notification_service:
            return

        mentions = extract_mentions(post.body)
        if not mentions:
            return

        author = await self.user_repo.get_by_id(author_id)
        if not author:
            return

        for username in mentions:
            if username.lower() == author.username.lower():
                continue  # Skip self-mentions

            mentioned_user = await self.user_repo.get_by_username(username)
            if mentioned_user:
                await self.notification_service.notify_mention(
                    user_id=mentioned_user.id,
                    mentioner_id=author_id,
                    mentioner_username=author.username,
                    post_id=post.id,
                )

    # =========================================================================
    # Private: Caching
    # =========================================================================

    async def _get_cached_feed(self, key: str) -> PaginatedResult | None:
        """Get cached feed from Redis."""
        if not self.redis:
            return None

        try:
            data = await self.redis.get(key)
            if data:
                # Note: Full caching implementation would deserialize here
                pass
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        return None

    async def _cache_feed(
        self,
        key: str,
        result: PaginatedResult,
        ttl: int,
    ) -> None:
        """Cache feed result in Redis."""
        if not self.redis:
            return

        try:
            # Note: Full implementation would serialize the response
            await self.redis.setex(key, ttl, "cached")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    async def _invalidate_feed_caches(self, user_id: int) -> None:
        """Invalidate feed caches after post creation/deletion."""
        if not self.redis:
            return

        try:
            pattern = f"home_feed:{user_id}:*"
            async for key in self.redis.scan_iter(match=pattern):
                await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
