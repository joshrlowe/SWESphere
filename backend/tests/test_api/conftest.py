"""
API test fixtures and configuration.

Provides fixtures for testing FastAPI routes with async SQLite database
and mocked Redis for isolated, fast testing.
"""

import asyncio
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.dependencies import get_db, get_redis


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Global password store for mock password hashing
_password_store: dict[str, str] = {}


def _mock_hash_password(password: str) -> str:
    """Mock password hashing for tests."""
    hashed = f"hashed_{password}"
    _password_store[hashed] = password
    return hashed


def _mock_verify_password(plain: str, hashed: str) -> bool:
    """Mock password verification for tests."""
    return _password_store.get(hashed) == plain


def _mock_validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """Mock password validation for tests."""
    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not any(c.isupper() for c in password):
        errors.append("uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("digit")
    return len(errors) == 0, errors


# Apply patches at module load time
_patches = [
    patch("app.core.security.hash_password", _mock_hash_password),
    patch("app.core.security.verify_password", _mock_verify_password),
    patch("app.core.security.validate_password_strength", _mock_validate_password_strength),
    patch("app.services.auth_service.hash_password", _mock_hash_password),
    patch("app.services.auth_service.verify_password", _mock_verify_password),
    patch("app.services.auth_service.validate_password_strength", _mock_validate_password_strength),
]

for p in _patches:
    p.start()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
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


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for tests."""
    async_session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session


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
    redis.keys = AsyncMock(return_value=[])
    return redis


@pytest_asyncio.fixture
async def test_app(db_engine, mock_redis):
    """Create FastAPI app with test database."""
    # Import here to ensure patches are applied
    from app.main import create_app
    
    # Clear password store for each test
    _password_store.clear()
    
    # Create test session factory
    async_session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async def override_get_db():
        session = async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def override_get_redis():
        return mock_redis

    # Create app and override dependencies
    application = create_app()
    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_redis] = override_get_redis

    yield application

    # Clean up
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a test user and return auth headers."""
    # Register a test user
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "username": "testuser",
            "password": "TestPass123!",
        },
    )
    assert response.status_code == 201, f"Registration failed: {response.text}"

    # Login to get tokens
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "TestPass123!",
        },
    )
    assert response.status_code == 200, f"Login failed: {response.text}"

    data = response.json()
    token = data["tokens"]["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def second_user_headers(client: AsyncClient) -> dict[str, str]:
    """Register a second test user and return auth headers."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "seconduser@example.com",
            "username": "seconduser",
            "password": "TestPass123!",
        },
    )
    assert response.status_code == 201

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "seconduser",
            "password": "TestPass123!",
        },
    )
    assert response.status_code == 200

    data = response.json()
    token = data["tokens"]["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user_data() -> dict[str, Any]:
    """Standard test user data."""
    return {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "SecurePass123!",
    }


@pytest.fixture
def test_post_data() -> dict[str, str]:
    """Standard test post data."""
    return {"body": "This is a test post! #testing @testuser"}
