"""Tests for WebSocket functionality."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import WebSocket

from app.core.websocket import (
    ConnectionManager,
    MessageType,
    build_message,
    build_notification_message,
    build_unread_count_message,
)
from app.services.realtime_service import RealtimeService


# =============================================================================
# Message Building Tests
# =============================================================================


class TestMessageBuilding:
    """Tests for message building utilities."""

    def test_build_message_with_data(self):
        """Test building a message with data."""
        message = build_message(MessageType.NOTIFICATION, {"id": 123})
        
        assert message["type"] == MessageType.NOTIFICATION
        assert message["data"]["id"] == 123
        assert "timestamp" in message

    def test_build_message_without_data(self):
        """Test building a message without data."""
        message = build_message(MessageType.PONG)
        
        assert message["type"] == MessageType.PONG
        assert message["data"] == {}
        assert "timestamp" in message

    def test_build_notification_message(self):
        """Test building a notification message."""
        actor = {"id": 1, "username": "john", "avatar_url": None}
        message = build_notification_message(
            notification_id=123,
            notification_type="new_follower",
            message="John started following you",
            actor=actor,
        )
        
        assert message["type"] == MessageType.NOTIFICATION
        assert message["data"]["id"] == 123
        assert message["data"]["type"] == "new_follower"
        assert message["data"]["message"] == "John started following you"
        assert message["data"]["actor"] == actor
        assert message["data"]["read"] is False

    def test_build_notification_message_with_extra_data(self):
        """Test building a notification with extra data."""
        message = build_notification_message(
            notification_id=1,
            notification_type="post_liked",
            message="Someone liked your post",
            extra_data={"post_id": 456},
        )
        
        assert message["data"]["post_id"] == 456

    def test_build_unread_count_message(self):
        """Test building an unread count message."""
        message = build_unread_count_message(5)
        
        assert message["type"] == MessageType.UNREAD_COUNT
        assert message["data"]["count"] == 5


# =============================================================================
# Connection Manager Tests
# =============================================================================


class TestConnectionManager:
    """Tests for the ConnectionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh connection manager."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock(spec=WebSocket)
        ws.send_json = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = AsyncMock()
        redis.publish = AsyncMock(return_value=1)
        redis.ping = AsyncMock()
        
        # Mock pubsub
        pubsub = AsyncMock()
        pubsub.subscribe = AsyncMock()
        pubsub.unsubscribe = AsyncMock()
        pubsub.close = AsyncMock()
        pubsub.get_message = AsyncMock(return_value=None)
        redis.pubsub = MagicMock(return_value=pubsub)
        
        return redis

    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self, manager, mock_websocket, mock_redis):
        """Test that connect accepts the WebSocket."""
        # Start manager without listener task
        manager._redis = mock_redis
        manager._pubsub = mock_redis.pubsub()
        
        await manager.connect(mock_websocket, user_id=1)
        
        mock_websocket.accept.assert_called_once()
        assert manager.is_user_connected(1)
        assert manager.connection_count == 1

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager, mock_websocket, mock_redis):
        """Test that disconnect removes the connection."""
        manager._redis = mock_redis
        manager._pubsub = mock_redis.pubsub()
        
        await manager.connect(mock_websocket, user_id=1)
        await manager.disconnect(mock_websocket, user_id=1)
        
        assert not manager.is_user_connected(1)
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_multiple_connections_per_user(self, manager, mock_redis):
        """Test handling multiple connections for a single user."""
        manager._redis = mock_redis
        manager._pubsub = mock_redis.pubsub()
        
        ws1 = AsyncMock(spec=WebSocket)
        ws1.send_json = AsyncMock()
        ws1.accept = AsyncMock()
        
        ws2 = AsyncMock(spec=WebSocket)
        ws2.send_json = AsyncMock()
        ws2.accept = AsyncMock()
        
        await manager.connect(ws1, user_id=1)
        await manager.connect(ws2, user_id=1)
        
        assert manager.is_user_connected(1)
        assert manager.connection_count == 2
        assert manager.user_count == 1

    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager, mock_redis):
        """Test sending a personal message via Redis."""
        manager._redis = mock_redis
        
        message = {"type": "test", "data": {}}
        result = await manager.send_personal_message(user_id=1, message=message)
        
        assert result is True
        mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast(self, manager, mock_redis):
        """Test broadcasting a message."""
        manager._redis = mock_redis
        
        message = {"type": "announcement", "data": {}}
        result = await manager.broadcast(message)
        
        assert result is True
        mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_direct(self, manager, mock_websocket):
        """Test sending directly to a WebSocket."""
        message = {"type": "pong", "data": {}}
        result = await manager.send_direct(mock_websocket, message)
        
        assert result is True
        mock_websocket.send_json.assert_called_once_with(message)

    def test_connection_count_empty(self, manager):
        """Test connection count is 0 when empty."""
        assert manager.connection_count == 0
        assert manager.user_count == 0

    def test_is_user_connected_false_when_not_connected(self, manager):
        """Test is_user_connected returns False for non-connected users."""
        assert not manager.is_user_connected(999)


# =============================================================================
# Realtime Service Tests
# =============================================================================


class TestRealtimeService:
    """Tests for the RealtimeService class."""

    @pytest.fixture
    def mock_manager(self):
        """Create a mock connection manager."""
        manager = MagicMock()
        manager.send_personal_message = AsyncMock(return_value=True)
        manager.broadcast = AsyncMock(return_value=True)
        manager.is_user_connected = MagicMock(return_value=True)
        manager.user_count = 5
        manager.connection_count = 10
        return manager

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock()
        user.id = 1
        user.username = "testuser"
        user.display_name = "Test User"
        user.avatar_url = "https://example.com/avatar.jpg"
        return user

    @pytest.fixture
    def service(self, mock_manager):
        """Create a realtime service with mocked manager."""
        svc = RealtimeService()
        svc._manager = mock_manager
        return svc

    @pytest.mark.asyncio
    async def test_notify_new_follower(self, service, mock_manager, mock_user):
        """Test sending new follower notification."""
        result = await service.notify_new_follower(
            user_id=2,
            follower=mock_user,
        )
        
        assert result is True
        mock_manager.send_personal_message.assert_called_once()
        # Args are positional: (user_id, message)
        call_args = mock_manager.send_personal_message.call_args[0]
        assert call_args[0] == 2  # user_id
        message = call_args[1]  # message
        assert message["data"]["type"] == "new_follower"
        assert "testuser" in message["data"]["message"]

    @pytest.mark.asyncio
    async def test_notify_post_liked(self, service, mock_manager, mock_user):
        """Test sending post liked notification."""
        result = await service.notify_post_liked(
            user_id=2,
            liker=mock_user,
            post_id=123,
        )
        
        assert result is True
        call_args = mock_manager.send_personal_message.call_args[0]
        message = call_args[1]
        assert message["data"]["type"] == "post_liked"
        assert message["data"]["post_id"] == 123

    @pytest.mark.asyncio
    async def test_notify_new_comment(self, service, mock_manager, mock_user):
        """Test sending new comment notification."""
        result = await service.notify_new_comment(
            user_id=2,
            commenter=mock_user,
            post_id=123,
            comment_id=456,
            comment_preview="This is a comment",
        )
        
        assert result is True
        call_args = mock_manager.send_personal_message.call_args[0]
        message = call_args[1]
        assert message["data"]["type"] == "new_comment"
        assert message["data"]["post_id"] == 123
        assert message["data"]["comment_id"] == 456

    @pytest.mark.asyncio
    async def test_notify_mention(self, service, mock_manager, mock_user):
        """Test sending mention notification."""
        result = await service.notify_mention(
            user_id=2,
            mentioner=mock_user,
            post_id=123,
        )
        
        assert result is True
        call_args = mock_manager.send_personal_message.call_args[0]
        message = call_args[1]
        assert message["data"]["type"] == "mention"

    @pytest.mark.asyncio
    async def test_send_unread_count_update(self, service, mock_manager):
        """Test sending unread count update."""
        result = await service.send_unread_count_update(user_id=1, count=5)
        
        assert result is True
        call_args = mock_manager.send_personal_message.call_args[0]
        message = call_args[1]
        assert message["type"] == MessageType.UNREAD_COUNT
        assert message["data"]["count"] == 5

    @pytest.mark.asyncio
    async def test_broadcast_announcement(self, service, mock_manager):
        """Test broadcasting announcement."""
        result = await service.broadcast_announcement(
            title="System Update",
            body="The system will be under maintenance.",
        )
        
        assert result is True
        mock_manager.broadcast.assert_called_once()

    def test_is_user_online(self, service, mock_manager):
        """Test checking if user is online."""
        assert service.is_user_online(1) is True
        mock_manager.is_user_connected.assert_called_with(1)

    def test_online_user_count(self, service, mock_manager):
        """Test getting online user count."""
        assert service.online_user_count == 5

    def test_total_connections(self, service, mock_manager):
        """Test getting total connections."""
        assert service.total_connections == 10


# =============================================================================
# WebSocket Stats Endpoint Test
# =============================================================================


@pytest.mark.asyncio
async def test_websocket_stats_endpoint(client):
    """Test the WebSocket stats endpoint."""
    response = await client.get("/api/v1/ws/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert "total_connections" in data
    assert "connected_users" in data

