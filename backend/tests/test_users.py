"""Tests for user endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User


@pytest.mark.asyncio
async def test_get_user_profile(
    client: AsyncClient, test_user: dict
) -> None:
    """Test getting a user's profile."""
    response = await client.get(f"/api/v1/users/{test_user['username']}")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user["username"]
    # Email should not be in public profile
    assert "email" not in data or data.get("email") is None


@pytest.mark.asyncio
async def test_get_nonexistent_user(client: AsyncClient) -> None:
    """Test getting a nonexistent user."""
    response = await client.get("/api/v1/users/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_profile(
    client: AsyncClient, auth_headers: dict
) -> None:
    """Test updating user profile."""
    response = await client.patch(
        "/api/v1/users/me",
        headers=auth_headers,
        json={
            "display_name": "Test User",
            "bio": "This is my bio",
            "location": "San Francisco",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Test User"
    assert data["bio"] == "This is my bio"
    assert data["location"] == "San Francisco"


@pytest.mark.asyncio
async def test_follow_user(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
) -> None:
    """Test following a user."""
    # Create another user to follow
    other_user = User(
        email="other@example.com",
        username="otheruser",
        password_hash=hash_password("TestPass123"),
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    # Follow the user
    response = await client.post(
        "/api/v1/users/otheruser/follow",
        headers=auth_headers,
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_unfollow_user(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
) -> None:
    """Test unfollowing a user."""
    # Create another user
    other_user = User(
        email="other@example.com",
        username="otheruser",
        password_hash=hash_password("TestPass123"),
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    # Follow then unfollow
    await client.post(
        "/api/v1/users/otheruser/follow",
        headers=auth_headers,
    )
    response = await client.delete(
        "/api/v1/users/otheruser/follow",
        headers=auth_headers,
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_followers(
    client: AsyncClient, test_user: dict
) -> None:
    """Test getting user's followers."""
    response = await client.get(
        f"/api/v1/users/{test_user['username']}/followers"
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_following(
    client: AsyncClient, test_user: dict
) -> None:
    """Test getting users that user follows."""
    response = await client.get(
        f"/api/v1/users/{test_user['username']}/following"
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

