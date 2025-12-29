"""
Tests for notification API routes.

Tests notification listing, marking as read, and deletion.
"""

import pytest
from httpx import AsyncClient


class TestNotificationList:
    """Tests for notification list endpoint."""

    @pytest.mark.asyncio
    async def test_get_notifications_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting notifications when empty."""
        response = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "unread_count" in data
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_notifications_after_follow(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test getting notifications after being followed."""
        # Second user follows first user
        await client.post(
            "/api/v1/users/testuser/follow",
            headers=second_user_headers,
        )

        # First user should have a notification
        response = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["unread_count"] >= 1

        # Verify notification type
        notification = data["items"][0]
        assert notification["type"] == "new_follower" or "follower" in str(
            notification["type"]
        ).lower()

    @pytest.mark.asyncio
    async def test_get_notifications_after_like(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test getting notifications after post is liked."""
        # First user creates a post
        post_response = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Like this post!"},
        )
        post_id = post_response.json()["id"]

        # Second user likes it
        await client.post(
            f"/api/v1/posts/{post_id}/like",
            headers=second_user_headers,
        )

        # First user should have a notification
        response = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_notifications_pagination(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test notification list pagination."""
        response = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
            params={"page": 1, "per_page": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert "pages" in data

    @pytest.mark.asyncio
    async def test_get_notifications_unread_only(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting only unread notifications."""
        response = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
            params={"unread_only": True},
        )

        assert response.status_code == 200
        data = response.json()
        # All returned notifications should be unread
        assert all(not n["read"] for n in data["items"])

    @pytest.mark.asyncio
    async def test_get_notifications_unauthenticated(self, client: AsyncClient):
        """Test getting notifications without auth fails."""
        response = await client.get("/api/v1/notifications/")

        assert response.status_code == 401


class TestUnreadCount:
    """Tests for unread count endpoint."""

    @pytest.mark.asyncio
    async def test_get_unread_count_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test unread count when no notifications."""
        response = await client.get(
            "/api/v1/notifications/unread-count",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] >= 0

    @pytest.mark.asyncio
    async def test_get_unread_count_after_notification(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test unread count after receiving notification."""
        # Get initial count
        initial = await client.get(
            "/api/v1/notifications/unread-count",
            headers=auth_headers,
        )
        initial_count = initial.json()["count"]

        # Second user follows first user (creates notification)
        await client.post(
            "/api/v1/users/testuser/follow",
            headers=second_user_headers,
        )

        # Check new count
        response = await client.get(
            "/api/v1/notifications/unread-count",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["count"] >= initial_count + 1

    @pytest.mark.asyncio
    async def test_get_unread_count_unauthenticated(self, client: AsyncClient):
        """Test unread count without auth fails."""
        response = await client.get("/api/v1/notifications/unread-count")

        assert response.status_code == 401


class TestMarkAsRead:
    """Tests for marking notifications as read."""

    @pytest.mark.asyncio
    async def test_mark_single_as_read(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test marking a single notification as read."""
        # Create notification by having second user follow
        await client.post(
            "/api/v1/users/testuser/follow",
            headers=second_user_headers,
        )

        # Get notifications
        notifs = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
        )
        notification_id = notifs.json()["items"][0]["id"]

        # Mark as read
        response = await client.post(
            f"/api/v1/notifications/{notification_id}/read",
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Verify it's marked as read
        updated = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
        )
        notification = next(
            (n for n in updated.json()["items"] if n["id"] == notification_id), None
        )
        assert notification is not None
        assert notification["read"] is True

    @pytest.mark.asyncio
    async def test_mark_nonexistent_as_read(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test marking non-existent notification fails gracefully."""
        response = await client.post(
            "/api/v1/notifications/99999/read",
            headers=auth_headers,
        )

        # Should handle gracefully (success: false or 404)
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_mark_all_as_read(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test marking all notifications as read."""
        # Create some notifications
        await client.post(
            "/api/v1/users/testuser/follow",
            headers=second_user_headers,
        )

        # Create a post and have it liked
        post = await client.post(
            "/api/v1/posts/",
            headers=auth_headers,
            json={"body": "Like me"},
        )
        await client.post(
            f"/api/v1/posts/{post.json()['id']}/like",
            headers=second_user_headers,
        )

        # Mark all as read
        response = await client.post(
            "/api/v1/notifications/read-all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "marked" in response.json()["message"].lower()

        # Verify unread count is 0
        count = await client.get(
            "/api/v1/notifications/unread-count",
            headers=auth_headers,
        )
        assert count.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_mark_as_read_unauthenticated(self, client: AsyncClient):
        """Test marking as read without auth fails."""
        response = await client.post("/api/v1/notifications/1/read")

        assert response.status_code == 401


class TestNotificationDeletion:
    """Tests for notification deletion endpoints."""

    @pytest.mark.asyncio
    async def test_delete_notification(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test deleting a single notification."""
        # Create notification
        await client.post(
            "/api/v1/users/testuser/follow",
            headers=second_user_headers,
        )

        # Get notification ID
        notifs = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
        )
        notification_id = notifs.json()["items"][0]["id"]

        # Delete it
        response = await client.delete(
            f"/api/v1/notifications/{notification_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify it's deleted
        updated = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
        )
        assert all(n["id"] != notification_id for n in updated.json()["items"])

    @pytest.mark.asyncio
    async def test_delete_others_notification(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test deleting someone else's notification fails."""
        # Create notification for first user
        await client.post(
            "/api/v1/users/testuser/follow",
            headers=second_user_headers,
        )

        # Get first user's notification
        notifs = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
        )
        notification_id = notifs.json()["items"][0]["id"]

        # Try to delete as second user
        response = await client.delete(
            f"/api/v1/notifications/{notification_id}",
            headers=second_user_headers,
        )

        # Should fail (404 or 403)
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_delete_all_read(
        self, client: AsyncClient, auth_headers: dict, second_user_headers: dict
    ):
        """Test deleting all read notifications."""
        # Create notifications
        await client.post(
            "/api/v1/users/testuser/follow",
            headers=second_user_headers,
        )

        # Mark all as read
        await client.post(
            "/api/v1/notifications/read-all",
            headers=auth_headers,
        )

        # Get count before deletion
        before = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
        )
        before_total = before.json()["total"]

        # Delete all read
        response = await client.delete(
            "/api/v1/notifications/",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify read notifications are deleted
        after = await client.get(
            "/api/v1/notifications/",
            headers=auth_headers,
        )
        # Should have fewer or same notifications
        assert after.json()["total"] <= before_total

    @pytest.mark.asyncio
    async def test_delete_unauthenticated(self, client: AsyncClient):
        """Test deleting without auth fails."""
        response = await client.delete("/api/v1/notifications/1")

        assert response.status_code == 401

