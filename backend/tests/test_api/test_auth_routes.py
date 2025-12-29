"""
Tests for authentication API routes.

Tests registration, login, logout, token refresh,
email verification, and password reset endpoints.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import get_error_message


class TestRegistration:
    """Tests for user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, test_user_data: dict):
        """Test successful user registration."""
        response = await client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, auth_headers: dict):
        """Test registration fails with duplicate email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "testuser@example.com",  # Already registered in auth_headers
                "username": "differentuser",
                "password": "TestPass123!",
            },
        )

        assert response.status_code == 400
        error_msg = get_error_message(response.json())
        assert "email" in error_msg

    @pytest.mark.asyncio
    async def test_register_duplicate_username(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test registration fails with duplicate username."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "different@example.com",
                "username": "testuser",  # Already registered in auth_headers
                "password": "TestPass123!",
            },
        )

        assert response.status_code == 400
        error_msg = get_error_message(response.json())
        assert "username" in error_msg

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration fails with invalid email format."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "username": "validuser",
                "password": "TestPass123!",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Test registration fails with weak password."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "valid@example.com",
                "username": "validuser",
                "password": "weak",  # Too short, no uppercase, no digit
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_username(self, client: AsyncClient):
        """Test registration fails with invalid username characters."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "valid@example.com",
                "username": "invalid user!",  # Spaces and special chars not allowed
                "password": "TestPass123!",
            },
        )

        assert response.status_code == 422


class TestLogin:
    """Tests for login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "TestPass123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["username"] == "testuser"
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
        assert data["tokens"]["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_with_email(self, client: AsyncClient, auth_headers: dict):
        """Test login with email instead of username."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser@example.com",  # Using email
                "password": "TestPass123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, auth_headers: dict):
        """Test login fails with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "WrongPass123!",
            },
        )

        assert response.status_code == 401
        error_msg = get_error_message(response.json())
        assert "invalid" in error_msg

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login fails for non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "AnyPass123!",
            },
        )

        assert response.status_code == 401


class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Refresh token verification depends on Redis storage")
    async def test_refresh_token_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful token refresh."""
        # First login to get refresh token
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "TestPass123!"},
        )
        refresh_token = login_response.json()["tokens"]["refresh_token"]

        # Use refresh token to get new tokens
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test refresh fails with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

        assert response.status_code == 401


class TestLogout:
    """Tests for logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful logout."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_logout_unauthenticated(self, client: AsyncClient):
        """Test logout fails without authentication."""
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 401


class TestCurrentUser:
    """Tests for current user endpoint."""

    @pytest.mark.asyncio
    async def test_get_me_success(self, client: AsyncClient, auth_headers: dict):
        """Test getting current user profile."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "testuser@example.com"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_me_unauthenticated(self, client: AsyncClient):
        """Test getting current user fails without auth."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401


class TestPasswordReset:
    """Tests for password reset endpoints."""

    @pytest.mark.asyncio
    async def test_request_password_reset_existing_email(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test requesting password reset for existing email."""
        response = await client.post(
            "/api/v1/auth/password-reset",
            json={"email": "testuser@example.com"},
        )

        # Should return success even if email exists (security)
        assert response.status_code == 200
        assert "success" in response.json()

    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_email(self, client: AsyncClient):
        """Test requesting password reset for non-existent email."""
        response = await client.post(
            "/api/v1/auth/password-reset",
            json={"email": "nonexistent@example.com"},
        )

        # Should return success even for non-existent email (security)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_confirm_password_reset_invalid_token(self, client: AsyncClient):
        """Test password reset confirmation with invalid token."""
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": "invalid-token",
                "new_password": "NewSecurePass123!",
            },
        )

        assert response.status_code == 400


class TestEmailVerification:
    """Tests for email verification endpoints."""

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, client: AsyncClient):
        """Test email verification with invalid token."""
        response = await client.post("/api/v1/auth/verify-email/invalid-token")

        assert response.status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Resend verification requires email service")
    async def test_resend_verification_authenticated(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test resending verification email when authenticated."""
        response = await client.post(
            "/api/v1/auth/resend-verification",
            headers=auth_headers,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_resend_verification_unauthenticated(self, client: AsyncClient):
        """Test resending verification fails without auth."""
        response = await client.post("/api/v1/auth/resend-verification")

        assert response.status_code == 401

