"""Post repository for data access."""

from sqlalchemy import delete, func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import followers, post_likes
from app.models.post import Post
from app.repositories.base import BaseRepository


class PostRepository(BaseRepository[Post]):
    """Repository for Post model operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize post repository."""
        super().__init__(db, Post)

    async def get_with_author(self, post_id: int) -> Post | None:
        """Get post with author loaded."""
        result = await self.db.execute(
            select(Post)
            .where(Post.id == post_id)
            .options(selectinload(Post.author))
        )
        return result.scalar_one_or_none()

    async def get_user_posts(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """Get posts by a specific user."""
        result = await self.db.execute(
            select(Post)
            .where(Post.user_id == user_id)
            .options(selectinload(Post.author))
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_feed(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """Get posts from users that the given user follows."""
        # Get posts from followed users and own posts
        result = await self.db.execute(
            select(Post)
            .join(
                followers,
                or_(
                    Post.user_id == followers.c.followed_id,
                    Post.user_id == user_id,
                ),
                isouter=True,
            )
            .where(
                or_(
                    followers.c.follower_id == user_id,
                    Post.user_id == user_id,
                )
            )
            .options(selectinload(Post.author))
            .order_by(Post.created_at.desc())
            .distinct()
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_explore(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """Get all posts for explore page."""
        result = await self.db.execute(
            select(Post)
            .options(selectinload(Post.author))
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search(
        self,
        query: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """Search posts by content."""
        search_pattern = f"%{query}%"
        result = await self.db.execute(
            select(Post)
            .where(Post.body.ilike(search_pattern))
            .options(selectinload(Post.author))
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def like(self, user_id: int, post_id: int) -> bool:
        """Like a post."""
        # Check if already liked
        existing = await self.db.execute(
            select(post_likes).where(
                post_likes.c.user_id == user_id,
                post_likes.c.post_id == post_id,
            )
        )
        if existing.first():
            return False

        await self.db.execute(
            insert(post_likes).values(user_id=user_id, post_id=post_id)
        )
        await self.db.flush()
        return True

    async def unlike(self, user_id: int, post_id: int) -> bool:
        """Unlike a post."""
        result = await self.db.execute(
            delete(post_likes).where(
                post_likes.c.user_id == user_id,
                post_likes.c.post_id == post_id,
            )
        )
        await self.db.flush()
        return result.rowcount > 0

    async def is_liked(self, user_id: int, post_id: int) -> bool:
        """Check if user has liked a post."""
        result = await self.db.execute(
            select(func.count())
            .select_from(post_likes)
            .where(
                post_likes.c.user_id == user_id,
                post_likes.c.post_id == post_id,
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

    async def get_replies(
        self,
        post_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """Get replies to a post."""
        result = await self.db.execute(
            select(Post)
            .where(Post.reply_to_id == post_id)
            .options(selectinload(Post.author))
            .order_by(Post.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
