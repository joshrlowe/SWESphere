"""
Tests for AuthService.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_register_success(user_repo: UserRepository, mock_redis, db_session):
    """Test successful user registration."""
    from app.schemas.user import UserCreate

    service = AuthService(user_repo, mock_redis)

    user_data = UserCreate(
        username="newuser",
        email="new@example.com",
        password="SecurePass123",
    )

    # Mock password hashing to avoid bcrypt issues
    with patch(
        "app.services.auth_service.hash_password", return_value="hashed_password"
    ):
        with patch(
            "app.services.auth_service.validate_password_strength",
            return_value=(True, []),
        ):
            user = await service.register(user_data)

    assert user.id is not None
    assert user.username == "newuser"
    assert user.email == "new@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(
    user_repo: UserRepository, mock_redis, user_factory
):
    """Test registration fails with duplicate email."""
    from app.schemas.user import UserCreate

    # Create existing user
    await user_factory(email="existing@example.com")

    service = AuthService(user_repo, mock_redis)

    user_data = UserCreate(
        username="newuser",
        email="existing@example.com",
        password="SecurePass123",
    )

    with patch(
        "app.services.auth_service.validate_password_strength", return_value=(True, [])
    ):
        with pytest.raises(HTTPException) as exc_info:
            await service.register(user_data)

    assert exc_info.value.status_code == 400
    assert "Email already registered" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_register_duplicate_username(
    user_repo: UserRepository, mock_redis, user_factory
):
    """Test registration fails with duplicate username."""
    from app.schemas.user import UserCreate

    await user_factory(username="existinguser")

    service = AuthService(user_repo, mock_redis)

    user_data = UserCreate(
        username="existinguser",
        email="new@example.com",
        password="SecurePass123",
    )

    with patch(
        "app.services.auth_service.validate_password_strength", return_value=(True, [])
    ):
        with pytest.raises(HTTPException) as exc_info:
            await service.register(user_data)

    assert exc_info.value.status_code == 400
    assert "Username already taken" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_login_success(user_repo: UserRepository, mock_redis, user_factory):
    """Test successful login."""
    # Create user with a known password hash
    user = await user_factory(
        username="loginuser",
        password_hash="hashed_password",
    )

    service = AuthService(user_repo, mock_redis)

    # Mock password verification
    with patch("app.services.auth_service.verify_password", return_value=True):
        result = await service.login("loginuser", "TestPass123")

    assert result.user.id == user.id
    assert result.tokens.access_token is not None
    assert result.tokens.refresh_token is not None


@pytest.mark.asyncio
async def test_login_invalid_password(
    user_repo: UserRepository, mock_redis, user_factory
):
    """Test login fails with wrong password."""
    await user_factory(
        username="loginuser",
        password_hash="hashed_password",
    )

    service = AuthService(user_repo, mock_redis)

    with patch("app.services.auth_service.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await service.login("loginuser", "WrongPass123")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_user_not_found(user_repo: UserRepository, mock_redis):
    """Test login fails for non-existent user."""
    service = AuthService(user_repo, mock_redis)

    with pytest.raises(HTTPException) as exc_info:
        await service.login("nonexistent", "anypassword")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_logout(user_repo: UserRepository, mock_redis, user_factory):
    """Test logout revokes refresh token."""
    user = await user_factory()

    service = AuthService(user_repo, mock_redis)

    await service.logout(user.id)

    # Verify Redis delete was called
    mock_redis.delete.assert_called()


@pytest.mark.asyncio
async def test_verify_email_success(
    user_repo: UserRepository, mock_redis, user_factory
):
    """Test email verification."""
    user = await user_factory(email_verified=False)

    # Mock Redis to return user ID for token
    mock_redis.get = AsyncMock(return_value=str(user.id).encode())

    service = AuthService(user_repo, mock_redis)

    result = await service.verify_email("valid_token")

    assert result.email_verified is True


@pytest.mark.asyncio
async def test_verify_email_invalid_token(user_repo: UserRepository, mock_redis):
    """Test email verification fails with invalid token."""
    mock_redis.get = AsyncMock(return_value=None)

    service = AuthService(user_repo, mock_redis)

    with pytest.raises(HTTPException) as exc_info:
        await service.verify_email("invalid_token")

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_request_password_reset(
    user_repo: UserRepository, mock_redis, user_factory
):
    """Test password reset request."""
    user = await user_factory(email="reset@example.com")

    service = AuthService(user_repo, mock_redis)

    # Should not raise even for existing user
    await service.request_password_reset("reset@example.com")

    # Token should be stored in Redis
    mock_redis.setex.assert_called()


@pytest.mark.asyncio
async def test_request_password_reset_nonexistent(
    user_repo: UserRepository, mock_redis
):
    """Test password reset request for non-existent email (should not reveal)."""
    service = AuthService(user_repo, mock_redis)

    # Should not raise even for non-existent user
    await service.request_password_reset("nonexistent@example.com")


@pytest.mark.asyncio
async def test_reset_password_success(
    user_repo: UserRepository, mock_redis, user_factory
):
    """Test password reset."""
    user = await user_factory()

    mock_redis.get = AsyncMock(return_value=str(user.id).encode())

    service = AuthService(user_repo, mock_redis)

    with patch(
        "app.services.auth_service.validate_password_strength", return_value=(True, [])
    ):
        with patch(
            "app.services.auth_service.hash_password",
            return_value="new_hashed_password",
        ):
            result = await service.reset_password("valid_token", "NewSecurePass123")

    assert result.id == user.id
    # Tokens should be deleted
    assert mock_redis.delete.called
