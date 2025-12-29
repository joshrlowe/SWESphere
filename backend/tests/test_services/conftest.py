"""
Test fixtures for service tests.

Provides mock repositories and Redis for isolated service testing.
"""

import asyncio
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.user import User
from app.models.post import Post
from app.models.notification import Notification, NotificationType
from app.repositories.user_repository import UserRepository
from app.repositories.post_repository import PostRepository


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for tests."""
    async_session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def user_repo(db_session: AsyncSession) -> UserRepository:
    """Create user repository."""
    return UserRepository(db_session)


@pytest_asyncio.fixture
async def post_repo(db_session: AsyncSession) -> PostRepository:
    """Create post repository."""
    return PostRepository(db_session)


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=False)
    redis.incr = AsyncMock(return_value=1)
    redis.decr = AsyncMock(return_value=0)
    redis.publish = AsyncMock(return_value=1)
    redis.scan_iter = MagicMock(return_value=iter([]))
    return redis


@pytest_asyncio.fixture
async def user_factory(db_session: AsyncSession):
    """Factory for creating test users."""
    counter = 0

    async def _create_user(**kwargs: Any) -> User:
        nonlocal counter
        counter += 1

        defaults = {
            "username": f"testuser{counter}",
            "email": f"test{counter}@example.com",
            "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VBCvZ/0LIqnPGy",  # "password"
            "is_active": True,
            "failed_login_attempts": 0,
            "locked_until": None,
        }
        defaults.update(kwargs)

        user = User(**defaults)
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    return _create_user


@pytest_asyncio.fixture
async def post_factory(db_session: AsyncSession, user_factory):
    """Factory for creating test posts."""
    counter = 0

    async def _create_post(author: User | None = None, **kwargs: Any) -> Post:
        nonlocal counter
        counter += 1

        if author is None:
            author = await user_factory()

        defaults = {
            "user_id": author.id,
            "body": f"Test post content {counter}",
        }
        defaults.update(kwargs)

        post = Post(**defaults)
        db_session.add(post)
        await db_session.flush()
        await db_session.refresh(post)
        return post

    return _create_post
