"""
Post repository for data access.

Handles all database operations for Post entities including:
- CRUD operations (inherited)
- Feed generation (home, explore)
- Like/unlike operations
- Post search
"""

import logging
from typing import Sequence

from sqlalchemy import case, delete, func, insert, or_, select
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
        condition = Post.user_id.in_(author_ids) if author_ids else Post.user_id == user_id
        
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
            select(func.count())
            .select_from(Post)
            .where(Post.deleted_at.is_(None))
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
                        (Post.likes_count > 0, Post.likes_count - 1),
                        else_=0
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
            select(post_likes.c.post_id)
            .where(
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
            select(followers_table.c.followed_id)
            .where(followers_table.c.follower_id == user_id)
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
