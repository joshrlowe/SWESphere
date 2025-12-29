"""
Post repository for data access.

Handles all database operations for Post entities including:
- CRUD operations (inherited)
- Feed generation (home, explore)
- Like/unlike operations
- Post search
- Optimized batch operations
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import case, delete, func, insert, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import followers, post_likes
from app.models.post import Post
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class PostRepository(BaseRepository[Post]):
    """Repository for Post model operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize post repository."""
        super().__init__(db, Post)

    # =========================================================================
    # Single Post Retrieval
    # =========================================================================

    async def get_with_author(self, post_id: int) -> Post | None:
        """
        Get post with author relationship eagerly loaded.

        Args:
            post_id: Post ID

        Returns:
            Post with author loaded, or None if not found
        """
        logger.debug(f"Fetching post {post_id} with author")
        result = await self.db.execute(
            select(Post)
            .where(Post.id == post_id)
            .where(Post.deleted_at.is_(None))
            .options(selectinload(Post.author))
        )
        return result.scalar_one_or_none()

    async def get_with_relationships(self, post_id: int) -> Post | None:
        """
        Get post with all relationships eagerly loaded.

        Args:
            post_id: Post ID

        Returns:
            Post with author, comments, liked_by loaded
        """
        result = await self.db.execute(
            select(Post)
            .where(Post.id == post_id)
            .where(Post.deleted_at.is_(None))
            .options(
                selectinload(Post.author),
                selectinload(Post.comments),
                selectinload(Post.liked_by),
            )
        )
        return result.scalar_one_or_none()

    # =========================================================================
    # Feed Generation
    # =========================================================================

    async def get_home_feed(
        self,
        user_id: int,
        following_ids: list[int],
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Post], int]:
        """
        Get personalized home feed for a user.

        Includes posts from:
        - Users the current user follows
        - The user's own posts

        Args:
            user_id: Current user's ID
            following_ids: List of user IDs being followed
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Tuple of (posts, total_count)
        """
        logger.debug(f"Generating home feed for user_id={user_id}")

        # Include own posts and posts from followed users
        author_ids = following_ids + [user_id]

        # Base condition
        condition = (
            Post.user_id.in_(author_ids) if author_ids else Post.user_id == user_id
        )

        # Get total count
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Post)
            .where(condition)
            .where(Post.deleted_at.is_(None))
        )
        total = count_result.scalar() or 0

        # Get paginated posts
        result = await self.db.execute(
            select(Post)
            .where(condition)
            .where(Post.deleted_at.is_(None))
            .options(selectinload(Post.author))
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all(), total

    async def get_explore_feed(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Post], int]:
        """
        Get explore/discovery feed (public posts).

        Returns recent posts from all users, sorted by recency.
        Could be enhanced with trending algorithms.

        Args:
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Tuple of (posts, total_count)
        """
        logger.debug("Generating explore feed")

        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(Post).where(Post.deleted_at.is_(None))
        )
        total = count_result.scalar() or 0

        # Get paginated posts
        result = await self.db.execute(
            select(Post)
            .where(Post.deleted_at.is_(None))
            .options(selectinload(Post.author))
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all(), total

    async def get_user_posts(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Post], int]:
        """
        Get all posts by a specific user.

        Args:
            user_id: User whose posts to fetch
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Tuple of (posts, total_count)
        """
        logger.debug(f"Fetching posts for user_id={user_id}")

        # Get total count
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Post)
            .where(Post.user_id == user_id)
            .where(Post.deleted_at.is_(None))
        )
        total = count_result.scalar() or 0

        # Get paginated posts
        result = await self.db.execute(
            select(Post)
            .where(Post.user_id == user_id)
            .where(Post.deleted_at.is_(None))
            .options(selectinload(Post.author))
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all(), total

    # =========================================================================
    # Like Operations
    # =========================================================================

    async def like_post(self, user_id: int, post_id: int) -> bool:
        """
        Add a like to a post.

        Args:
            user_id: User liking the post
            post_id: Post being liked

        Returns:
            True if like was added, False if already liked
        """
        # Check if already liked
        if await self.is_liked_by(post_id, user_id):
            logger.debug(f"User {user_id} already liked post {post_id}")
            return False

        await self.db.execute(
            insert(post_likes).values(user_id=user_id, post_id=post_id)
        )

        # Update denormalized count
        await self.db.execute(
            Post.__table__.update()
            .where(Post.id == post_id)
            .values(likes_count=Post.likes_count + 1)
        )

        await self.db.flush()
        logger.info(f"User {user_id} liked post {post_id}")
        return True

    async def unlike_post(self, user_id: int, post_id: int) -> bool:
        """
        Remove a like from a post.

        Args:
            user_id: User unliking the post
            post_id: Post being unliked

        Returns:
            True if like was removed, False if wasn't liked
        """
        result = await self.db.execute(
            delete(post_likes).where(
                post_likes.c.user_id == user_id,
                post_likes.c.post_id == post_id,
            )
        )

        if result.rowcount > 0:
            # Update denormalized count (using CASE for SQLite compatibility)
            await self.db.execute(
                Post.__table__.update()
                .where(Post.id == post_id)
                .values(
                    likes_count=case(
                        (Post.likes_count > 0, Post.likes_count - 1), else_=0
                    )
                )
            )
            await self.db.flush()
            logger.info(f"User {user_id} unliked post {post_id}")
            return True

        return False

    async def is_liked_by(self, post_id: int, user_id: int) -> bool:
        """
        Check if a post is liked by a specific user.

        Args:
            post_id: Post to check
            user_id: User to check

        Returns:
            True if user has liked the post
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(post_likes)
            .where(
                post_likes.c.post_id == post_id,
                post_likes.c.user_id == user_id,
            )
        )
        return (result.scalar() or 0) > 0

    async def get_likes_count(self, post_id: int) -> int:
        """Get number of likes for a post."""
        result = await self.db.execute(
            select(func.count())
            .select_from(post_likes)
            .where(post_likes.c.post_id == post_id)
        )
        return result.scalar() or 0

    async def get_liked_post_ids(
        self,
        user_id: int,
        post_ids: list[int],
    ) -> set[int]:
        """
        Get which posts from a list are liked by a user.

        Useful for batch-checking likes when displaying a feed.

        Args:
            user_id: User to check likes for
            post_ids: List of post IDs to check

        Returns:
            Set of post IDs that the user has liked
        """
        if not post_ids:
            return set()

        result = await self.db.execute(
            select(post_likes.c.post_id).where(
                post_likes.c.user_id == user_id,
                post_likes.c.post_id.in_(post_ids),
            )
        )
        return {row[0] for row in result.fetchall()}

    # =========================================================================
    # Replies
    # =========================================================================

    async def get_replies(
        self,
        post_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Post], int]:
        """
        Get replies to a specific post.

        Args:
            post_id: Parent post ID
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Tuple of (replies, total_count)
        """
        logger.debug(f"Fetching replies to post_id={post_id}")

        # Get total count
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Post)
            .where(Post.reply_to_id == post_id)
            .where(Post.deleted_at.is_(None))
        )
        total = count_result.scalar() or 0

        # Get paginated replies
        result = await self.db.execute(
            select(Post)
            .where(Post.reply_to_id == post_id)
            .where(Post.deleted_at.is_(None))
            .options(selectinload(Post.author))
            .order_by(Post.created_at.asc())
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all(), total

    # =========================================================================
    # Search
    # =========================================================================

    async def search_posts(
        self,
        query: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Post], int]:
        """
        Search posts by content.

        Args:
            query: Search term
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Tuple of (posts, total_count)
        """
        logger.debug(f"Searching posts with query: {query}")
        search_pattern = f"%{query}%"

        # Get total count
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Post)
            .where(Post.body.ilike(search_pattern))
            .where(Post.deleted_at.is_(None))
        )
        total = count_result.scalar() or 0

        # Get paginated results
        result = await self.db.execute(
            select(Post)
            .where(Post.body.ilike(search_pattern))
            .where(Post.deleted_at.is_(None))
            .options(selectinload(Post.author))
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all(), total

    # =========================================================================
    # Optimized Feed Methods (N+1 query elimination)
    # =========================================================================

    async def get_home_feed_optimized(
        self,
        following_ids: list[int],
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Post], int]:
        """
        Optimized home feed query with eager loading.

        Uses single query with selectinload for author.
        Uses denormalized counts instead of querying likes table.

        Args:
            following_ids: List of user IDs being followed (include own ID for own posts)
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Tuple of (posts, total_count)
        """
        logger.debug(f"Generating optimized home feed for {len(following_ids)} following")

        if not following_ids:
            return [], 0

        # Base condition - posts from followed users
        condition = Post.user_id.in_(following_ids)

        # Get total count in single query
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Post)
            .where(condition)
            .where(Post.deleted_at.is_(None))
        )
        total = count_result.scalar() or 0

        # Single optimized query with eager loading
        # Uses covering index: idx_posts_user_timestamp
        result = await self.db.execute(
            select(Post)
            .where(condition)
            .where(Post.deleted_at.is_(None))
            .options(selectinload(Post.author))
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all(), total

    async def get_posts_with_like_status(
        self,
        post_ids: list[int],
        user_id: int,
    ) -> dict[int, bool]:
        """
        Batch query to check like status for multiple posts.

        Eliminates N+1 queries when checking likes for a feed of posts.

        Args:
            post_ids: List of post IDs to check
            user_id: User whose like status to check

        Returns:
            Dictionary mapping post_id -> is_liked (True/False)
        """
        if not post_ids:
            return {}

        logger.debug(f"Batch checking likes for {len(post_ids)} posts, user_id={user_id}")

        # Single query to get all liked post IDs
        result = await self.db.execute(
            select(post_likes.c.post_id).where(
                post_likes.c.user_id == user_id,
                post_likes.c.post_id.in_(post_ids),
            )
        )
        liked_post_ids = {row[0] for row in result.fetchall()}

        # Return dict with True for liked, False for not liked
        return {post_id: post_id in liked_post_ids for post_id in post_ids}

    async def get_explore_feed_optimized(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        hours: int = 24,
    ) -> tuple[Sequence[Post], int]:
        """
        Optimized explore feed with database-side scoring.

        Scoring formula: likes + (comments * 2) + recency_bonus
        Recency bonus: posts from last `hours` get extra points

        Uses covering index: idx_posts_timestamp_engagement

        Args:
            skip: Pagination offset
            limit: Maximum results
            hours: Hours to consider for recency bonus (default 24)

        Returns:
            Tuple of (posts, total_count)
        """
        logger.debug(f"Generating optimized explore feed with {hours}h recency window")

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Engagement score calculated in database
        # likes_count + (comments_count * 2) + recency_bonus
        recency_bonus = case(
            (Post.created_at >= cutoff_time, literal(10)),
            else_=literal(0),
        )
        engagement_score = (
            Post.likes_count + (Post.comments_count * 2) + recency_bonus
        )

        # Get total count for non-deleted posts
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Post)
            .where(Post.deleted_at.is_(None))
        )
        total = count_result.scalar() or 0

        # Get posts ordered by engagement score
        result = await self.db.execute(
            select(Post)
            .where(Post.deleted_at.is_(None))
            .options(selectinload(Post.author))
            .order_by(engagement_score.desc(), Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all(), total

    async def get_trending_posts(
        self,
        *,
        hours: int = 6,
        limit: int = 10,
    ) -> Sequence[Post]:
        """
        Get trending posts based on recent engagement velocity.

        Calculates engagement rate (likes + comments) within time window.

        Args:
            hours: Time window for trending calculation
            limit: Maximum results

        Returns:
            List of trending posts
        """
        logger.debug(f"Fetching trending posts from last {hours} hours")

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Posts created within time window, ordered by engagement
        result = await self.db.execute(
            select(Post)
            .where(Post.deleted_at.is_(None))
            .where(Post.created_at >= cutoff_time)
            .options(selectinload(Post.author))
            .order_by(
                (Post.likes_count + Post.comments_count * 2).desc(),
                Post.created_at.desc(),
            )
            .limit(limit)
        )

        return result.scalars().all()

    async def get_posts_by_ids_ordered(
        self,
        post_ids: list[int],
    ) -> Sequence[Post]:
        """
        Get posts by IDs maintaining the input order.

        Useful for displaying cached feed results.

        Args:
            post_ids: Ordered list of post IDs

        Returns:
            Posts in same order as input IDs
        """
        if not post_ids:
            return []

        result = await self.db.execute(
            select(Post)
            .where(Post.id.in_(post_ids))
            .where(Post.deleted_at.is_(None))
            .options(selectinload(Post.author))
        )

        posts = result.scalars().all()

        # Reorder to match input order
        post_map = {post.id: post for post in posts}
        return [post_map[pid] for pid in post_ids if pid in post_map]

    # =========================================================================
    # Legacy Aliases (for backwards compatibility)
    # =========================================================================

    async def get_feed(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Post]:
        """Legacy method - use get_home_feed instead."""
        # Get following IDs
        from app.models import followers as followers_table

        result = await self.db.execute(
            select(followers_table.c.followed_id).where(
                followers_table.c.follower_id == user_id
            )
        )
        following_ids = [row[0] for row in result.fetchall()]

        posts, _ = await self.get_home_feed(
            user_id, following_ids, skip=skip, limit=limit
        )
        return posts

    async def get_explore(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Post]:
        """Legacy method - use get_explore_feed instead."""
        posts, _ = await self.get_explore_feed(skip=skip, limit=limit)
        return posts

    async def search(
        self,
        query: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Post]:
        """Legacy method - use search_posts instead."""
        posts, _ = await self.search_posts(query, skip=skip, limit=limit)
        return posts

    # Alias for consistent naming
    like = like_post
    unlike = unlike_post
    is_liked = is_liked_by
