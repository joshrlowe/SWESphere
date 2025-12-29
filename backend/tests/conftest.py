"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.dependencies import get_db, get_redis


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# =============================================================================
# Password Store for Testing
# =============================================================================

_password_store: dict[str, str] = {}


def mock_hash_password(password: str) -> str:
    """Mock password hashing that stores the mapping."""
    hashed = f"hashed_{password}"
    _password_store[hashed] = password
    return hashed


def mock_verify_password(plain_password: str, hashed_password: str) -> bool:
    """Mock password verification using the stored mapping."""
    return _password_store.get(hashed_password) == plain_password


def mock_validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """Mock password validation for tests."""
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain an uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain a lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain a digit")
    return len(errors) == 0, errors


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def mock_password_security():
    """Mock password hashing for all tests."""
    _password_store.clear()
    with patch("app.core.security.hash_password", side_effect=mock_hash_password):
        with patch("app.core.security.verify_password", side_effect=mock_verify_password):
            with patch("app.core.security.validate_password_strength", side_effect=mock_validate_password_strength):
                with patch("app.services.auth_service.hash_password", side_effect=mock_hash_password):
                    with patch("app.services.auth_service.verify_password", side_effect=mock_verify_password):
                        with patch("app.services.auth_service.validate_password_strength", side_effect=mock_validate_password_strength):
                            yield


@pytest.fixture
def mock_redis():
    """Create a mock async Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.setex = AsyncMock(return_value=True)
    redis.incr = AsyncMock(return_value=1)
    redis.decr = AsyncMock(return_value=0)
    redis.exists = AsyncMock(return_value=False)
    redis.expire = AsyncMock(return_value=True)
    redis.keys = AsyncMock(return_value=[])
    redis.publish = AsyncMock(return_value=1)
    redis.scan_iter = MagicMock(return_value=iter([]))
    return redis


@pytest_asyncio.fixture(scope="function")
async def db_session(mock_redis) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    # Drop all tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, mock_redis) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override."""
    from app.main import create_app

    test_app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        try:
            yield db_session
            await db_session.commit()
            # Expire all to ensure next request gets fresh data
            db_session.expire_all()
        except Exception:
            await db_session.rollback()
            raise

    async def override_get_redis():
        return mock_redis

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as ac:
        yield ac

    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> dict[str, Any]:
    """Create a test user."""
    from app.models.user import User

    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=mock_hash_password("TestPass123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "password": "TestPass123",
    }


@pytest_asyncio.fixture
async def auth_headers(test_user: dict[str, Any]) -> dict[str, str]:
    """Get authorization headers for test user."""
    from app.core.security import create_access_token

    token = create_access_token(subject=test_user["id"])
    return {"Authorization": f"Bearer {token}"}
