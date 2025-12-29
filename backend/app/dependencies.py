"""
Dependency injection container.

Provides FastAPI dependencies for:
- Database sessions
- Redis client
- Repositories
- Services

All dependencies are designed for async operation and proper resource management.
"""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_async_session
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.notification_service import NotificationService
from app.services.post_service import PostService
from app.services.user_service import UserService


# =============================================================================
# Database Dependencies
# =============================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for request handling.

    The session is automatically committed on success or rolled back on error.
    """
    async for session in get_async_session():
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]


# =============================================================================
# Redis Dependencies
# =============================================================================


class RedisManager:
    """
    Manages Redis client lifecycle.

    Provides lazy initialization and proper cleanup of Redis connections.
    """

    _client: Redis | None = None

    @classmethod
    async def get_client(cls) -> Redis:
        """Get or create the Redis client."""
        if cls._client is None:
            cls._client = Redis.from_url(
                str(settings.REDIS_URL),
                decode_responses=True,
            )
        return cls._client

    @classmethod
    async def close(cls) -> None:
        """Close the Redis connection if open."""
        if cls._client is not None:
            await cls._client.close()
            cls._client = None


async def get_redis() -> Redis:
    """Provide Redis client for request handling."""
    return await RedisManager.get_client()


async def close_redis() -> None:
    """Close Redis connection during shutdown."""
    await RedisManager.close()


RedisClient = Annotated[Redis, Depends(get_redis)]


# =============================================================================
# Repository Dependencies
# =============================================================================


def get_user_repository(db: DBSession) -> UserRepository:
    """Provide UserRepository instance."""
    return UserRepository(db)


def get_post_repository(db: DBSession) -> PostRepository:
    """Provide PostRepository instance."""
    return PostRepository(db)


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
PostRepo = Annotated[PostRepository, Depends(get_post_repository)]


# =============================================================================
# Service Dependencies
# =============================================================================


def get_auth_service(user_repo: UserRepo, redis: RedisClient) -> AuthService:
    """Provide AuthService instance."""
    return AuthService(user_repo, redis)


def get_user_service(user_repo: UserRepo) -> UserService:
    """Provide UserService instance."""
    return UserService(user_repo)


def get_post_service(post_repo: PostRepo, user_repo: UserRepo) -> PostService:
    """Provide PostService instance."""
    return PostService(post_repo, user_repo)


def get_notification_service(db: DBSession, redis: RedisClient) -> NotificationService:
    """Provide NotificationService instance."""
    return NotificationService(db, redis)


AuthSvc = Annotated[AuthService, Depends(get_auth_service)]
UserSvc = Annotated[UserService, Depends(get_user_service)]
PostSvc = Annotated[PostService, Depends(get_post_service)]
NotificationSvc = Annotated[NotificationService, Depends(get_notification_service)]
