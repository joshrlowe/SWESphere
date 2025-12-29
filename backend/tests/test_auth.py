"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import get_error_message


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient) -> None:
    """Test user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePass123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert "password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: dict) -> None:
    """Test registration with duplicate email."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user["email"],
            "username": "differentuser",
            "password": "SecurePass123",
        },
    )
    assert response.status_code == 400
    error_msg = get_error_message(response.json())
    assert "already registered" in error_msg or "email" in error_msg


@pytest.mark.asyncio
async def test_register_duplicate_username(
    client: AsyncClient, test_user: dict
) -> None:
    """Test registration with duplicate username."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "different@example.com",
            "username": test_user["username"],
            "password": "SecurePass123",
        },
    )
    assert response.status_code == 400
    error_msg = get_error_message(response.json())
    assert "already taken" in error_msg or "username" in error_msg


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: dict) -> None:
    """Test successful login."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user["username"],
            "password": test_user["password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "tokens" in data
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]
    assert data["user"]["username"] == test_user["username"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: dict) -> None:
    """Test login with wrong password."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user["username"],
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_headers: dict, test_user: dict) -> None:
    """Test getting current user."""
    response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient) -> None:
    """Test getting current user without auth."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
