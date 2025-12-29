"""
Post service.

Handles post creation, retrieval, updates, likes, feed generation,
and mention processing.

Implements caching strategies:
- Cache-aside for feed queries
- Write-through for like counters
- Invalidation on post/follow changes
"""

import html
import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.pagination import PaginatedResult, calculate_skip
from app.core.redis_keys import CacheKeys, redis_keys
from app.models.comment import Comment
from app.models.post import Post
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.schemas.post import PostCreate, PostUpdate

if TYPE_CHECKING:
    from app.services.cache_invalidation import CacheInvalidator
    from app.services.cache_service import CacheService
    from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


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
    - Feed generation (home and explore) with caching
    - Like/unlike operations with write-through counters
    - Comment operations
    - Mention detection and notifications

    Caching Strategy:
    - Feeds: Cache-aside with 60s TTL (home) / 5min TTL (explore)
    - Like counts: Write-through to Redis counters
    - Like status: Cached in Redis sets for O(1) lookup
    """

    def __init__(
        self,
        post_repo: PostRepository,
        user_repo: UserRepository,
        redis: Redis | None = None,
        notification_service: "NotificationService | None" = None,
        cache: "CacheService | None" = None,
        cache_invalidator: "CacheInvalidator | None" = None,
    ) -> None:
        """
        Initialize post service.

        Args:
            post_repo: Post repository for data access
            user_repo: User repository for mention lookups
            redis: Optional Redis client for pub/sub
            notification_service: Optional notification service for mentions/likes
            cache: Optional cache service for caching operations
            cache_invalidator: Optional cache invalidator for cache management
        """
        self.post_repo = post_repo
        self.user_repo = user_repo
        self.redis = redis
        self.notification_service = notification_service
        self._cache = cache
        self._cache_invalidator = cache_invalidator

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

        # Invalidate feed caches (author + followers)
        if self._cache_invalidator:
            follower_ids = await self.user_repo.get_follower_ids(user_id)
            await self._cache_invalidator.on_new_post(post, user_id, follower_ids)
        else:
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
            # Invalidate caches
            if self._cache_invalidator:
                follower_ids = await self.user_repo.get_follower_ids(user_id)
                await self._cache_invalidator.on_post_delete(
                    post_id, user_id, follower_ids
                )
            else:
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
        Results are cached for performance using cache-aside pattern.

        Caching Strategy:
        1. Check cache first (60s TTL)
        2. On miss, query database
        3. Cache result before returning
        """
        cache_key = CacheKeys.home_feed_page(user_id, page, per_page)

        # Try cache first (cache-aside pattern)
        if self._cache:
            cached_data = await self._cache.get_json(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache HIT for home feed: user={user_id}, page={page}")
                return self._deserialize_feed_result(cached_data)

        # Cache miss - query database
        skip = calculate_skip(page, per_page)
        following_ids = await self.user_repo.get_following_ids(user_id)
        posts, total = await self.post_repo.get_home_feed(
            user_id,
            following_ids=following_ids,
            skip=skip,
            limit=per_page,
        )

        result = PaginatedResult.create(list(posts), total, page, per_page)

        # Cache the result
        if self._cache:
            serialized = self._serialize_feed_result(result)
            await self._cache.set_json(cache_key, serialized, FEED_CACHE_TTL)
            logger.debug(f"Cache SET for home feed: user={user_id}, page={page}")

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
        Results are cached for performance (5 min TTL).
        """
        cache_key = CacheKeys.explore_feed_page(page, per_page)

        # Try cache first
        if self._cache:
            cached_data = await self._cache.get_json(cache_key)
            if cached_data is not None:
                logger.debug(f"Cache HIT for explore feed: page={page}")
                return self._deserialize_feed_result(cached_data)

        # Cache miss - query database
        skip = calculate_skip(page, per_page)
        posts, total = await self.post_repo.get_explore_feed(skip=skip, limit=per_page)
        result = PaginatedResult.create(list(posts), total, page, per_page)

        # Cache the result
        if self._cache:
            serialized = self._serialize_feed_result(result)
            await self._cache.set_json(cache_key, serialized, EXPLORE_CACHE_TTL)
            logger.debug(f"Cache SET for explore feed: page={page}")

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

        Uses write-through pattern: updates both DB and cache atomically.

        Returns:
            True if like was added (False if already liked)

        Raises:
            HTTPException: If post not found
        """
        post = await self._verify_post_exists(post_id)
        success = await self.post_repo.like_post(user_id, post_id)

        if success:
            # Write-through: update cache counter
            if self._cache_invalidator:
                await self._cache_invalidator.on_like(user_id, post_id)

            await self._send_like_notification(post, user_id)
            logger.debug(f"User {user_id} liked post {post_id}")

        return success

    async def unlike_post(self, user_id: int, post_id: int) -> bool:
        """
        Remove like from a post.

        Uses write-through pattern for cache consistency.

        Returns:
            True if like was removed (False if wasn't liked)
        """
        success = await self.post_repo.unlike_post(user_id, post_id)
        if success:
            # Write-through: update cache counter
            if self._cache_invalidator:
                await self._cache_invalidator.on_unlike(user_id, post_id)

            logger.debug(f"User {user_id} unliked post {post_id}")
        return success

    async def is_liked(self, user_id: int, post_id: int) -> bool:
        """
        Check if a user has liked a specific post.

        Checks cache first for O(1) lookup.
        """
        # Try cache first
        if self._cache:
            is_cached = await self._cache.is_in_set(
                CacheKeys.post_likers(post_id),
                str(user_id),
            )
            # Only trust cache hit if the set exists
            set_exists = await self._cache.exists(CacheKeys.post_likers(post_id))
            if set_exists:
                return is_cached

        return await self.post_repo.is_liked_by(post_id, user_id)

    async def get_liked_status(
        self,
        user_id: int,
        post_ids: list[int],
    ) -> dict[int, bool]:
        """
        Check like status for multiple posts at once.

        Uses cache when available for better performance.

        Returns:
            Dict mapping post_id -> is_liked
        """
        result: dict[int, bool] = {}
        uncached_ids: list[int] = []

        # Check cache for each post
        if self._cache:
            for post_id in post_ids:
                set_exists = await self._cache.exists(CacheKeys.post_likers(post_id))
                if set_exists:
                    is_liked = await self._cache.is_in_set(
                        CacheKeys.post_likers(post_id),
                        str(user_id),
                    )
                    result[post_id] = is_liked
                else:
                    uncached_ids.append(post_id)
        else:
            uncached_ids = post_ids

        # Query DB for uncached posts
        if uncached_ids:
            liked_ids = await self.post_repo.get_liked_post_ids(user_id, uncached_ids)
            for post_id in uncached_ids:
                result[post_id] = post_id in liked_ids

        return result

    async def get_like_count(self, post_id: int) -> int:
        """
        Get the like count for a post.

        Checks cache first, falls back to database.

        Args:
            post_id: Post ID

        Returns:
            Number of likes
        """
        # Try cache first
        if self._cache:
            cached_count = await self._cache.get_counter(
                CacheKeys.post_likes_count(post_id)
            )
            if cached_count is not None:
                return cached_count

        # Query database
        count = await self.post_repo.get_likes_count(post_id)

        # Warm cache
        if self._cache:
            await self._cache.set_counter(
                CacheKeys.post_likes_count(post_id),
                count,
            )

        return count

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

    def _serialize_feed_result(self, result: PaginatedResult) -> dict[str, Any]:
        """
        Serialize a PaginatedResult for caching.

        Converts Post objects to dicts for JSON storage.
        """
        return {
            "items": [self._serialize_post(post) for post in result.items],
            "total": result.total,
            "page": result.page,
            "per_page": result.per_page,
            "pages": result.pages,
            "has_next": result.has_next,
            "has_prev": result.has_prev,
        }

    def _serialize_post(self, post: Post) -> dict[str, Any]:
        """Serialize a Post for caching."""
        return {
            "id": post.id,
            "body": post.body,
            "user_id": post.user_id,
            "media_url": post.media_url,
            "media_type": post.media_type,
            "likes_count": post.likes_count,
            "comments_count": post.comments_count,
            "reposts_count": getattr(post, "reposts_count", 0),
            "reply_to_id": post.reply_to_id,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "updated_at": post.updated_at.isoformat() if post.updated_at else None,
            # Include author info if loaded
            "author": self._serialize_author(post.author) if post.author else None,
        }

    @staticmethod
    def _serialize_author(author) -> dict[str, Any]:
        """Serialize author info for caching."""
        return {
            "id": author.id,
            "username": author.username,
            "display_name": author.display_name,
            "avatar_url": author.avatar_url,
        }

    def _deserialize_feed_result(self, data: dict[str, Any]) -> PaginatedResult:
        """
        Deserialize a cached feed result.

        Note: Returns raw dicts, not Post objects.
        For full ORM objects, a cache miss is needed.
        """
        from app.core.pagination import PaginatedResult

        return PaginatedResult(
            items=data.get("items", []),
            total=data.get("total", 0),
            page=data.get("page", 1),
            per_page=data.get("per_page", 20),
            pages=data.get("pages", 1),
            has_next=data.get("has_next", False),
            has_prev=data.get("has_prev", False),
        )

    async def _get_cached_feed(self, key: str) -> PaginatedResult | None:
        """Get cached feed from Redis (legacy method)."""
        if not self.redis:
            return None

        try:
            data = await self.redis.get(key)
            if data:
                parsed = json.loads(data)
                return self._deserialize_feed_result(parsed)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        return None

    async def _cache_feed(
        self,
        key: str,
        result: PaginatedResult,
        ttl: int,
    ) -> None:
        """Cache feed result in Redis (legacy method)."""
        if not self.redis:
            return

        try:
            serialized = json.dumps(self._serialize_feed_result(result), default=str)
            await self.redis.setex(key, ttl, serialized)
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    async def _invalidate_feed_caches(self, user_id: int) -> None:
        """Invalidate feed caches after post creation/deletion."""
        if self._cache_invalidator:
            await self._cache_invalidator.invalidate_user_feeds(user_id)
            return

        if not self.redis:
            return

        try:
            pattern = f"home_feed:{user_id}:*"
            async for key in self.redis.scan_iter(match=pattern):
                await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
