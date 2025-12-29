"""User repository for data access."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import followers
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize user repository."""
        super().__init__(db, User)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email_or_username(
        self, email: str, username: str
    ) -> User | None:
        """Get user by email or username."""
        result = await self.db.execute(
            select(User).where(or_(User.email == email, User.username == username))
        )
        return result.scalar_one_or_none()

    async def get_with_relationships(self, user_id: int) -> User | None:
        """Get user with all relationships loaded."""
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.posts),
                selectinload(User.followers),
                selectinload(User.following),
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        query: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """Search users by username or display name."""
        search_pattern = f"%{query}%"
        result = await self.db.execute(
            select(User)
            .where(
                or_(
                    User.username.ilike(search_pattern),
                    User.display_name.ilike(search_pattern),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_followers(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """Get user's followers."""
        result = await self.db.execute(
            select(User)
            .join(followers, followers.c.follower_id == User.id)
            .where(followers.c.followed_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_following(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """Get users that this user is following."""
        result = await self.db.execute(
            select(User)
            .join(followers, followers.c.followed_id == User.id)
            .where(followers.c.follower_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_followers_count(self, user_id: int) -> int:
        """Get count of user's followers."""
        result = await self.db.execute(
            select(func.count())
            .select_from(followers)
            .where(followers.c.followed_id == user_id)
        )
        return result.scalar() or 0

    async def get_following_count(self, user_id: int) -> int:
        """Get count of users being followed."""
        result = await self.db.execute(
            select(func.count())
            .select_from(followers)
            .where(followers.c.follower_id == user_id)
        )
        return result.scalar() or 0

    async def is_following(self, follower_id: int, followed_id: int) -> bool:
        """Check if user is following another user."""
        result = await self.db.execute(
            select(func.count())
            .select_from(followers)
            .where(
                followers.c.follower_id == follower_id,
                followers.c.followed_id == followed_id,
            )
        )
        return (result.scalar() or 0) > 0

    async def follow(self, follower_id: int, followed_id: int) -> bool:
        """Follow a user."""
        if follower_id == followed_id:
            return False
        if await self.is_following(follower_id, followed_id):
            return False

        await self.db.execute(
            followers.insert().values(
                follower_id=follower_id, followed_id=followed_id
            )
        )
        await self.db.flush()
        return True

    async def unfollow(self, follower_id: int, followed_id: int) -> bool:
        """Unfollow a user."""
        result = await self.db.execute(
            followers.delete().where(
                followers.c.follower_id == follower_id,
                followers.c.followed_id == followed_id,
            )
        )
        await self.db.flush()
        return result.rowcount > 0

