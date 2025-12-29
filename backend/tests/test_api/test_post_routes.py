"""
Tests for post API routes.

Tests CRUD operations, feeds, likes, comments, and search.
"""

import pytest
from httpx import AsyncClient


class TestPostCreation:
    """Tests for post creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_post(
        self, client: AsyncClient, auth_headers: dict, test_post_data: dict
    ):
        """Test creating a new post."""
        response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json=test_post_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["body"] == test_post_data["body"]
        assert "id" in data
        assert "author" in data
        assert data["author"]["username"] == "testuser"
        assert data["likes_count"] == 0
        assert data["comments_count"] == 0

    @pytest.mark.asyncio
    async def test_create_post_empty(self, client: AsyncClient, auth_headers: dict):
        """Test creating empty post fails."""
        response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": ""},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_post_too_long(self, client: AsyncClient, auth_headers: dict):
        """Test creating post over 280 chars fails."""
        response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "x" * 281},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_post_unauthenticated(
        self, client: AsyncClient, test_post_data: dict
    ):
        """Test creating post without auth fails."""
        response = await client.post(
            "/api/v1/posts/",
            json=test_post_data,
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_reply(self, client: AsyncClient, auth_headers: dict):
        """Test creating a reply to a post."""
        # Create original post
        original = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Original post"},
        )
        post_id = original.json()["id"]

        # Create reply
        response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "This is a reply", "reply_to_id": post_id},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["reply_to_id"] == post_id


class TestPostRetrieval:
    """Tests for post retrieval endpoints."""

    @pytest.mark.asyncio
    async def test_get_post(self, client: AsyncClient, auth_headers: dict):
        """Test getting a single post."""
        # Create a post
        create_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Test post for retrieval"},
        )
        post_id = create_response.json()["id"]

        # Get the post
        response = await client.get(f"/api/v1/posts/{post_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == post_id
        assert data["body"] == "Test post for retrieval"
        assert "comments" in data  # PostDetailResponse includes comments
        assert "comments_total" in data

    @pytest.mark.asyncio
    async def test_get_post_with_auth(self, client: AsyncClient, auth_headers: dict):
        """Test getting post shows like status when authenticated."""
        # Create a post
        create_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Post to like"},
        )
        post_id = create_response.json()["id"]

        # Like the post
        await client.post(f"/api/v1/posts/{post_id}/like", headers=auth_headers)

        # Get post with auth
        response = await client.get(
            f"/api/v1/posts/{post_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_liked"] is True

    @pytest.mark.asyncio
    async def test_get_nonexistent_post(self, client: AsyncClient):
        """Test getting non-existent post returns 404."""
        response = await client.get("/api/v1/posts/99999")

        assert response.status_code == 404


class TestPostUpdate:
    """Tests for post update endpoint."""

    @pytest.mark.asyncio
    async def test_update_post(self, client: AsyncClient, auth_headers: dict):
        """Test updating a post."""
        # Create a post
        create_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Original content"},
        )
        post_id = create_response.json()["id"]

        # Update the post
        response = await client.patch(
            f"/api/v1/posts/{post_id}",
            headers=auth_headers,
            json={"body": "Updated content"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["body"] == "Updated content"

    @pytest.mark.asyncio
    async def test_update_others_post(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test updating someone else's post fails."""
        # Create a post as first user
        create_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "First user's post"},
        )
        post_id = create_response.json()["id"]

        # Try to update as second user
        response = await client.patch(
            f"/api/v1/posts/{post_id}",
            headers=second_user_headers,
            json={"body": "Trying to update"},
        )

        assert response.status_code == 403


class TestPostDeletion:
    """Tests for post deletion endpoint."""

    @pytest.mark.asyncio
    async def test_delete_post(self, client: AsyncClient, auth_headers: dict):
        """Test deleting own post."""
        # Create a post
        create_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Post to delete"},
        )
        post_id = create_response.json()["id"]

        # Delete the post
        response = await client.delete(
            f"/api/v1/posts/{post_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify it's deleted
        get_response = await client.get(f"/api/v1/posts/{post_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_others_post(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test deleting someone else's post fails."""
        # Create a post as first user
        create_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "First user's post"},
        )
        post_id = create_response.json()["id"]

        # Try to delete as second user
        response = await client.delete(
            f"/api/v1/posts/{post_id}",
            headers=second_user_headers,
        )

        assert response.status_code == 403


class TestFeeds:
    """Tests for feed endpoints."""

    @pytest.mark.asyncio
    async def test_get_explore_feed(self, client: AsyncClient, auth_headers: dict):
        """Test getting explore feed."""
        # Create some posts
        await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Explore post 1"},
        )
        await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Explore post 2"},
        )

        # Get explore feed (public endpoint)
        response = await client.get("/api/v1/posts/explore")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert data["total"] >= 2

    @pytest.mark.asyncio
    async def test_get_explore_feed_pagination(self, client: AsyncClient):
        """Test explore feed pagination."""
        response = await client.get(
            "/api/v1/posts/explore",
            params={"page": 1, "per_page": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 5

    @pytest.mark.asyncio
    async def test_get_home_feed(self, client: AsyncClient, auth_headers: dict):
        """Test getting personalized home feed."""
        response = await client.get(
            "/api/v1/posts/feed",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_home_feed_unauthenticated(self, client: AsyncClient):
        """Test home feed requires authentication."""
        response = await client.get("/api/v1/posts/feed")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_posts(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test getting a user's posts."""
        # Create posts as first user
        await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "User post 1"},
        )
        await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "User post 2"},
        )

        # Get first user's posts
        response = await client.get("/api/v1/posts/user/testuser")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert all(p["author"]["username"] == "testuser" for p in data["items"])


class TestLikes:
    """Tests for like/unlike endpoints."""

    @pytest.mark.asyncio
    async def test_like_post(self, client: AsyncClient, auth_headers: dict):
        """Test liking a post."""
        # Create a post
        create_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Post to like"},
        )
        post_id = create_response.json()["id"]

        # Like the post
        response = await client.post(
            f"/api/v1/posts/{post_id}/like",
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Verify like count increased
        get_response = await client.get(f"/api/v1/posts/{post_id}")
        assert get_response.json()["likes_count"] == 1

    @pytest.mark.asyncio
    async def test_unlike_post(self, client: AsyncClient, auth_headers: dict):
        """Test unliking a post."""
        # Create a post
        create_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Post to unlike"},
        )
        post_id = create_response.json()["id"]

        # Like then unlike
        await client.post(f"/api/v1/posts/{post_id}/like", headers=auth_headers)
        response = await client.delete(
            f"/api/v1/posts/{post_id}/like",
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Verify like count decreased
        get_response = await client.get(f"/api/v1/posts/{post_id}")
        assert get_response.json()["likes_count"] == 0

    @pytest.mark.asyncio
    async def test_like_unauthenticated(self, client: AsyncClient, auth_headers: dict):
        """Test liking without auth fails."""
        # Create a post
        create_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Post"},
        )
        post_id = create_response.json()["id"]

        response = await client.post(f"/api/v1/posts/{post_id}/like")

        assert response.status_code == 401


class TestComments:
    """Tests for comment endpoints."""

    @pytest.mark.asyncio
    async def test_create_comment(self, client: AsyncClient, auth_headers: dict):
        """Test creating a comment on a post."""
        # Create a post
        create_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Post to comment on"},
        )
        post_id = create_response.json()["id"]

        # Add a comment
        response = await client.post(
            f"/api/v1/posts/{post_id}/comments",
            headers=auth_headers,
            json={"body": "This is a comment"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["body"] == "This is a comment"
        assert data["post_id"] == post_id
        assert "author" in data

    @pytest.mark.asyncio
    async def test_get_comments(self, client: AsyncClient, auth_headers: dict):
        """Test getting comments for a post."""
        # Create a post
        create_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Post with comments"},
        )
        post_id = create_response.json()["id"]

        # Add comments
        await client.post(
            f"/api/v1/posts/{post_id}/comments",
            headers=auth_headers,
            json={"body": "Comment 1"},
        )
        await client.post(
            f"/api/v1/posts/{post_id}/comments",
            headers=auth_headers,
            json={"body": "Comment 2"},
        )

        # Get comments
        response = await client.get(f"/api/v1/posts/{post_id}/comments")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 2

    @pytest.mark.asyncio
    async def test_create_nested_comment(self, client: AsyncClient, auth_headers: dict):
        """Test creating a reply to a comment."""
        # Create a post
        create_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Post"},
        )
        post_id = create_response.json()["id"]

        # Create parent comment
        comment_response = await client.post(
            f"/api/v1/posts/{post_id}/comments",
            headers=auth_headers,
            json={"body": "Parent comment"},
        )
        parent_id = comment_response.json()["id"]

        # Create nested reply
        response = await client.post(
            f"/api/v1/posts/{post_id}/comments",
            headers=auth_headers,
            json={"body": "Reply to comment", "parent_id": parent_id},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["parent_id"] == parent_id

    @pytest.mark.asyncio
    async def test_delete_own_comment(self, client: AsyncClient, auth_headers: dict):
        """Test deleting own comment."""
        # Create post and comment
        post_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Post"},
        )
        post_id = post_response.json()["id"]

        comment_response = await client.post(
            f"/api/v1/posts/{post_id}/comments",
            headers=auth_headers,
            json={"body": "Comment to delete"},
        )
        comment_id = comment_response.json()["id"]

        # Delete comment
        response = await client.delete(
            f"/api/v1/posts/{post_id}/comments/{comment_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204


class TestPostSearch:
    """Tests for post search endpoint."""

    @pytest.mark.asyncio
    async def test_search_posts(self, client: AsyncClient, auth_headers: dict):
        """Test searching for posts."""
        # Create searchable posts
        await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Python programming is awesome"},
        )
        await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "I love Python development"},
        )

        # Search
        response = await client.get(
            "/api/v1/posts/search",
            params={"q": "python"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert all("python" in p["body"].lower() for p in data["items"])

    @pytest.mark.asyncio
    async def test_search_posts_no_results(self, client: AsyncClient):
        """Test search with no results."""
        response = await client.get(
            "/api/v1/posts/search",
            params={"q": "xyznonexistent"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestReplies:
    """Tests for post replies endpoint."""

    @pytest.mark.asyncio
    async def test_get_replies(self, client: AsyncClient, auth_headers: dict):
        """Test getting replies to a post."""
        # Create original post
        post_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Original post"},
        )
        post_id = post_response.json()["id"]

        # Create replies
        await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Reply 1", "reply_to_id": post_id},
        )
        await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Reply 2", "reply_to_id": post_id},
        )

        # Get replies
        response = await client.get(f"/api/v1/posts/{post_id}/replies")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

