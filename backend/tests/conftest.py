"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.dependencies import get_db, get_redis


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


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
async def db_engine():
    """Create and dispose async engine for each test."""
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


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine, mock_redis) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async_session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


def create_test_app() -> FastAPI:
    """
    Create a FastAPI app for testing without background tasks.
    
    This avoids the WebSocket listener infinite loop issue.
    """
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import ORJSONResponse
    
    from app.api.router import api_router
    from app.config import settings
    
    # Create a minimal lifespan that doesn't start background tasks
    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        # Skip WebSocket manager startup during tests
        yield
    
    app = FastAPI(
        title="SWESphere Test",
        default_response_class=ORJSONResponse,
        lifespan=test_lifespan,
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    return app


@pytest_asyncio.fixture(scope="function")
async def client(db_engine, db_session: AsyncSession, mock_redis) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override."""
    # Create session factory bound to this test's engine
    async_session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    
    # Use test app without background tasks
    test_app = create_test_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
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


# =============================================================================
# Session Cleanup Hook
# =============================================================================


def pytest_sessionfinish(session, exitstatus):
    """Clean up any remaining async resources after all tests complete."""
    # Force close any remaining event loop tasks
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.stop()
    except RuntimeError:
        pass


# =============================================================================
# Test Helpers
# =============================================================================


def get_error_message(response_json: dict) -> str:
    """
    Extract error message from API response.

    Handles both formats:
    - FastAPI default: {"detail": "..."}
    - Wrapped format: {"error": {"message": "..."}}

    Returns lowercase string for easier assertion matching.
    """
    # Try FastAPI default format first
    detail = response_json.get("detail", "")
    if isinstance(detail, str) and detail:
        return detail.lower()

    # Try wrapped format
    error_msg = response_json.get("error", {}).get("message", "")
    if error_msg:
        return error_msg.lower()

    # Return detail if it's a list (validation errors)
    if isinstance(detail, list):
        return str(detail).lower()

    return ""
