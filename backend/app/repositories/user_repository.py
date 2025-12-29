"""
User repository for data access.

Handles all database operations for User entities including:
- CRUD operations (inherited)
- Authentication lookups
- Social graph (followers/following)
- User search
"""

import logging
from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import followers
from app.models.user import User
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize user repository."""
        super().__init__(db, User)

    # =========================================================================
    # Authentication Lookups
    # =========================================================================

    async def get_by_email(self, email: str) -> User | None:
        """
        Get user by email address.

        Args:
            email: Email to search for (case-insensitive)

        Returns:
            User if found, None otherwise
        """
        logger.debug(f"Looking up user by email: {email}")
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """
        Get user by username.

        Args:
            username: Username to search for (case-insensitive)

        Returns:
            User if found, None otherwise
        """
        logger.debug(f"Looking up user by username: {username}")
        result = await self.db.execute(
            select(User).where(func.lower(User.username) == username.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_email_or_username(
        self,
        email: str,
        username: str,
    ) -> User | None:
        """
        Get user by email or username (for registration validation).

        Args:
            email: Email to check
            username: Username to check

        Returns:
            User if either matches, None otherwise
        """
        result = await self.db.execute(
            select(User).where(
                or_(
                    func.lower(User.email) == email.lower(),
                    func.lower(User.username) == username.lower(),
                )
            )
        )
        return result.scalar_one_or_none()

    # =========================================================================
    # User with Relationships
    # =========================================================================

    async def get_with_relationships(self, user_id: int) -> User | None:
        """
        Get user with all relationships eagerly loaded.

        Args:
            user_id: User ID

        Returns:
            User with posts, followers, following loaded
        """
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

    # =========================================================================
    # Followers / Following
    # =========================================================================

    async def get_followers(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[User]:
        """
        Get users who follow the specified user.

        Args:
            user_id: User whose followers to fetch
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Sequence of User objects
        """
        logger.debug(f"Fetching followers for user_id={user_id}")
        result = await self.db.execute(
            select(User)
            .join(followers, followers.c.follower_id == User.id)
            .where(followers.c.followed_id == user_id)
            .where(User.is_active.is_(True))
            .order_by(followers.c.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_following(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[User]:
        """
        Get users that the specified user follows.

        Args:
            user_id: User whose following list to fetch
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Sequence of User objects
        """
        logger.debug(f"Fetching following for user_id={user_id}")
        result = await self.db.execute(
            select(User)
            .join(followers, followers.c.followed_id == User.id)
            .where(followers.c.follower_id == user_id)
            .where(User.is_active.is_(True))
            .order_by(followers.c.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_following_ids(self, user_id: int) -> list[int]:
        """
        Get IDs of all users that the specified user follows.

        Useful for feed generation without loading full user objects.

        Args:
            user_id: User whose following IDs to fetch

        Returns:
            List of user IDs
        """
        result = await self.db.execute(
            select(followers.c.followed_id).where(followers.c.follower_id == user_id)
        )
        return [row[0] for row in result.fetchall()]

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
        """
        Check if one user follows another.

        Args:
            follower_id: Potential follower's user ID
            followed_id: Potential followed user's ID

        Returns:
            True if follower_id follows followed_id
        """
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
        """
        Create a follow relationship.

        Args:
            follower_id: User who wants to follow
            followed_id: User to be followed

        Returns:
            True if follow was created, False if already following or same user
        """
        if follower_id == followed_id:
            logger.warning(f"User {follower_id} attempted to follow themselves")
            return False

        if await self.is_following(follower_id, followed_id):
            logger.debug(f"User {follower_id} already follows {followed_id}")
            return False

        await self.db.execute(
            followers.insert().values(
                follower_id=follower_id,
                followed_id=followed_id,
            )
        )
        await self.db.flush()

        logger.info(f"User {follower_id} now follows {followed_id}")
        return True

    async def unfollow(self, follower_id: int, followed_id: int) -> bool:
        """
        Remove a follow relationship.

        Args:
            follower_id: User who wants to unfollow
            followed_id: User to be unfollowed

        Returns:
            True if unfollow succeeded, False if wasn't following
        """
        result = await self.db.execute(
            followers.delete().where(
                followers.c.follower_id == follower_id,
                followers.c.followed_id == followed_id,
            )
        )
        await self.db.flush()

        unfollowed = result.rowcount > 0
        if unfollowed:
            logger.info(f"User {follower_id} unfollowed {followed_id}")

        return unfollowed

    # =========================================================================
    # Search
    # =========================================================================

    async def search_users(
        self,
        query: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[User], int]:
        """
        Search users by username or display name.

        Args:
            query: Search term
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Tuple of (users, total_count)
        """
        logger.debug(f"Searching users with query: {query}")
        search_pattern = f"%{query}%"

        # Build base condition
        search_condition = or_(
            User.username.ilike(search_pattern),
            User.display_name.ilike(search_pattern),
        )

        # Get total count
        count_result = await self.db.execute(
            select(func.count())
            .select_from(User)
            .where(search_condition)
            .where(User.is_active.is_(True))
        )
        total = count_result.scalar() or 0

        # Get paginated results
        result = await self.db.execute(
            select(User)
            .where(search_condition)
            .where(User.is_active.is_(True))
            .order_by(User.followers_count.desc())
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all(), total

    # Backwards compatibility alias
    search = search_users

    # =========================================================================
    # Paginated Followers/Following (with counts)
    # =========================================================================

    async def get_followers_paginated(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[User], int]:
        """
        Get followers with total count for pagination.

        Args:
            user_id: User whose followers to fetch
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Tuple of (users, total_count)
        """
        # Get total count
        total = await self.get_followers_count(user_id)

        # Get paginated results
        users = await self.get_followers(user_id, skip=skip, limit=limit)

        return users, total

    async def get_following_paginated(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[User], int]:
        """
        Get following with total count for pagination.

        Args:
            user_id: User whose following list to fetch
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Tuple of (users, total_count)
        """
        # Get total count
        total = await self.get_following_count(user_id)

        # Get paginated results
        users = await self.get_following(user_id, skip=skip, limit=limit)

        return users, total

    # =========================================================================
    # Discovery / Suggestions
    # =========================================================================

    async def get_popular_users(
        self,
        *,
        exclude_ids: set[int] | None = None,
        limit: int = 10,
    ) -> Sequence[User]:
        """
        Get popular users for suggestions.

        Ordered by follower count descending.

        Args:
            exclude_ids: User IDs to exclude (e.g., already following)
            limit: Maximum results

        Returns:
            Sequence of popular User objects
        """
        query = (
            select(User)
            .where(User.is_active.is_(True))
            .order_by(User.followers_count.desc())
            .limit(limit)
        )

        if exclude_ids:
            query = query.where(User.id.notin_(exclude_ids))

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_id(self, user_id: int) -> User | None:
        """
        Get user by ID.

        Overrides base to ensure we only get active users.

        Args:
            user_id: User ID

        Returns:
            User if found and active, None otherwise
        """
        return await super().get(user_id)
