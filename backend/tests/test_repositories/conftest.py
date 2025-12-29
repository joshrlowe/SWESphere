"""
Test fixtures for repository tests.
"""

from typing import Any, AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.user import User
from app.models.post import Post


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    """Create async engine for tests with proper cleanup."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # StaticPool keeps the same connection for in-memory SQLite
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
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
        try:
            yield session
        finally:
            await session.rollback()


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
            "password_hash": "hashed_password",
            "is_active": True,
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
            "body": f"Test post {counter}",
        }
        defaults.update(kwargs)

        post = Post(**defaults)
        db_session.add(post)
        await db_session.flush()
        await db_session.refresh(post)
        return post

    return _create_post
