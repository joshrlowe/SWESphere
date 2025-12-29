"""User service for user operations."""

from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserPasswordUpdate, UserUpdate


class UserService:
    """Service for user operations."""

    def __init__(self, user_repo: UserRepository) -> None:
        """Initialize user service."""
        self.user_repo = user_repo

    async def get_user(self, user_id: int) -> User:
        """Get user by ID."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def get_user_by_username(self, username: str) -> User:
        """Get user by username."""
        user = await self.user_repo.get_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def update_profile(self, user_id: int, data: UserUpdate) -> User:
        """Update user profile."""
        user = await self.user_repo.update(
            user_id,
            **data.model_dump(exclude_unset=True),
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def update_password(
        self, user_id: int, data: UserPasswordUpdate
    ) -> None:
        """Update user password."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not verify_password(data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        await self.user_repo.update(
            user_id,
            password_hash=hash_password(data.new_password),
        )

    async def follow_user(self, follower_id: int, followed_id: int) -> bool:
        """Follow another user."""
        if follower_id == followed_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot follow yourself",
            )

        followed = await self.user_repo.get_by_id(followed_id)
        if not followed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return await self.user_repo.follow(follower_id, followed_id)

    async def unfollow_user(self, follower_id: int, followed_id: int) -> bool:
        """Unfollow a user."""
        return await self.user_repo.unfollow(follower_id, followed_id)

    async def get_followers(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """Get user's followers."""
        return await self.user_repo.get_followers(user_id, skip=skip, limit=limit)

    async def get_following(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """Get users that this user is following."""
        return await self.user_repo.get_following(user_id, skip=skip, limit=limit)

    async def search_users(
        self,
        query: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        """Search users."""
        return await self.user_repo.search(query, skip=skip, limit=limit)

    async def is_following(self, follower_id: int, followed_id: int) -> bool:
        """Check if user is following another user."""
        return await self.user_repo.is_following(follower_id, followed_id)

