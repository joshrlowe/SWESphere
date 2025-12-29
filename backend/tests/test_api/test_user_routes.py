"""
Tests for user API routes.

Tests profile management, following, followers, and search endpoints.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import get_error_message


class TestCurrentUserProfile:
    """Tests for current user profile endpoints."""

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict):
        """Test getting current user profile."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "testuser@example.com"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_current_user_unauthenticated(self, client: AsyncClient):
        """Test getting current user fails without auth."""
        response = await client.get("/api/v1/users/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_profile(self, client: AsyncClient, auth_headers: dict):
        """Test updating user profile."""
        response = await client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={
                "display_name": "Test User",
                "bio": "This is my test bio",
                "location": "Test City",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Test User"
        assert data["bio"] == "This is my test bio"
        assert data["location"] == "Test City"

    @pytest.mark.asyncio
    async def test_update_username(self, client: AsyncClient, auth_headers: dict):
        """Test updating username."""
        response = await client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"username": "updateduser"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "updateduser"

    @pytest.mark.asyncio
    async def test_update_username_taken(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test updating to taken username fails."""
        response = await client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"username": "seconduser"},  # Already taken
        )

        assert response.status_code == 400
        error_msg = get_error_message(response.json())
        assert "username" in error_msg

    @pytest.mark.asyncio
    async def test_update_profile_invalid_username(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating with invalid username fails."""
        response = await client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"username": "in valid!"},  # Invalid chars
        )

        assert response.status_code == 422


class TestPublicProfile:
    """Tests for public user profile endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_profile(self, client: AsyncClient, auth_headers: dict):
        """Test getting another user's public profile."""
        response = await client.get("/api/v1/users/testuser")

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert "email" not in data  # Email should be private
        assert "followers_count" in data
        assert "following_count" in data

    @pytest.mark.asyncio
    async def test_get_user_profile_with_auth(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test getting user profile shows follow status when authenticated."""
        # Follow the user first
        await client.post("/api/v1/users/testuser/follow", headers=second_user_headers)

        response = await client.get(
            "/api/v1/users/testuser",
            headers=second_user_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_following"] is True

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, client: AsyncClient):
        """Test getting non-existent user returns 404."""
        response = await client.get("/api/v1/users/nonexistent")

        assert response.status_code == 404


class TestFollowing:
    """Tests for follow/unfollow endpoints."""

    @pytest.mark.asyncio
    async def test_follow_user(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test following a user."""
        response = await client.post(
            "/api/v1/users/testuser/follow",
            headers=second_user_headers,
        )

        assert response.status_code == 200
        assert "following" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_follow_self(self, client: AsyncClient, auth_headers: dict):
        """Test following yourself fails."""
        response = await client.post(
            "/api/v1/users/testuser/follow",
            headers=auth_headers,
        )

        assert response.status_code == 400
        error_msg = get_error_message(response.json())
        assert "yourself" in error_msg or "cannot follow" in error_msg

    @pytest.mark.asyncio
    async def test_follow_nonexistent_user(self, client: AsyncClient, auth_headers: dict):
        """Test following non-existent user fails."""
        response = await client.post(
            "/api/v1/users/nonexistent/follow",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_follow_unauthenticated(self, client: AsyncClient, auth_headers: dict):
        """Test following without auth fails."""
        response = await client.post("/api/v1/users/testuser/follow")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_unfollow_user(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test unfollowing a user."""
        # First follow
        await client.post("/api/v1/users/testuser/follow", headers=second_user_headers)

        # Then unfollow
        response = await client.delete(
            "/api/v1/users/testuser/follow",
            headers=second_user_headers,
        )

        assert response.status_code == 200
        assert "unfollowed" in response.json()["message"].lower()


class TestFollowersList:
    """Tests for followers/following list endpoints."""

    @pytest.mark.asyncio
    async def test_get_followers(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test getting user's followers list."""
        # Create a follow relationship
        await client.post("/api/v1/users/testuser/follow", headers=second_user_headers)

        response = await client.get("/api/v1/users/testuser/followers")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert data["total"] >= 1
        assert any(u["username"] == "seconduser" for u in data["items"])

    @pytest.mark.asyncio
    async def test_get_followers_pagination(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test followers list pagination."""
        response = await client.get(
            "/api/v1/users/testuser/followers",
            params={"page": 1, "per_page": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert "pages" in data

    @pytest.mark.asyncio
    async def test_get_following(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test getting user's following list."""
        # Create a follow relationship
        await client.post("/api/v1/users/testuser/follow", headers=second_user_headers)

        response = await client.get("/api/v1/users/seconduser/following")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1
        assert any(u["username"] == "testuser" for u in data["items"])


class TestUserSearch:
    """Tests for user search endpoint."""

    @pytest.mark.asyncio
    async def test_search_users(self, client: AsyncClient, auth_headers: dict):
        """Test searching for users."""
        response = await client.get(
            "/api/v1/users/search",
            params={"q": "test"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        assert any(u["username"] == "testuser" for u in data["items"])

    @pytest.mark.asyncio
    async def test_search_users_pagination(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test user search pagination."""
        response = await client.get(
            "/api/v1/users/search",
            params={"q": "user", "page": 1, "per_page": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 5

    @pytest.mark.asyncio
    async def test_search_users_no_results(self, client: AsyncClient):
        """Test user search with no results."""
        response = await client.get(
            "/api/v1/users/search",
            params={"q": "xyznonexistent"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    @pytest.mark.asyncio
    async def test_search_users_empty_query(self, client: AsyncClient):
        """Test user search with empty query fails."""
        response = await client.get(
            "/api/v1/users/search",
            params={"q": ""},
        )

        assert response.status_code == 422  # Validation error

