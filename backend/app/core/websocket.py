"""
WebSocket connection management with Redis pub/sub for horizontal scaling.

Provides real-time notification delivery to connected clients across
multiple application instances.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from redis.asyncio.client import PubSub

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Redis channel names
BROADCAST_CHANNEL = "ws:broadcast"
USER_CHANNEL_PREFIX = "ws:user:"

# Message types
class MessageType:
    """WebSocket message types."""
    
    NOTIFICATION = "notification"
    UNREAD_COUNT = "unread_count"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    CONNECTED = "connected"
    MARK_READ = "mark_read"
    TYPING = "typing"


# =============================================================================
# Message Builders
# =============================================================================


def build_message(msg_type: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Build a standardized WebSocket message.
    
    Args:
        msg_type: Message type from MessageType
        data: Optional message payload
        
    Returns:
        Formatted message dictionary
    """
    return {
        "type": msg_type,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_notification_message(
    notification_id: int,
    notification_type: str,
    message: str,
    actor: dict[str, Any] | None = None,
    extra_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a notification message.
    
    Args:
        notification_id: Database ID of the notification
        notification_type: Type of notification (e.g., 'new_follower')
        message: Human-readable notification message
        actor: Optional actor information (user who triggered)
        extra_data: Optional additional data
        
    Returns:
        Formatted notification message
    """
    data = {
        "id": notification_id,
        "type": notification_type,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "read": False,
    }
    
    if actor:
        data["actor"] = actor
    
    if extra_data:
        data.update(extra_data)
    
    return build_message(MessageType.NOTIFICATION, data)


def build_unread_count_message(count: int) -> dict[str, Any]:
    """Build an unread count update message."""
    return build_message(MessageType.UNREAD_COUNT, {"count": count})


# =============================================================================
# Connection Manager
# =============================================================================


class ConnectionManager:
    """
    Manages WebSocket connections with Redis pub/sub for multi-instance support.
    
    Features:
    - Track active connections per user (supports multiple devices)
    - Publish messages via Redis for cross-instance delivery
    - Subscribe to user-specific and broadcast channels
    - Automatic reconnection handling
    
    Usage:
        manager = ConnectionManager()
        await manager.startup(redis_url)
        
        # In WebSocket endpoint:
        await manager.connect(websocket, user_id)
        try:
            while True:
                data = await websocket.receive_json()
                # Handle messages...
        except WebSocketDisconnect:
            await manager.disconnect(websocket, user_id)
    """
    
    def __init__(self) -> None:
        """Initialize the connection manager."""
        # Maps user_id -> set of WebSocket connections
        self._active_connections: dict[int, set[WebSocket]] = {}
        
        # Redis client and pubsub
        self._redis: Redis | None = None
        self._pubsub: PubSub | None = None
        self._listener_task: asyncio.Task | None = None
        
        # Shutdown flag
        self._shutdown: bool = False
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def startup(self, redis: Redis) -> None:
        """
        Initialize the connection manager with Redis.
        
        Args:
            redis: Redis client instance
        """
        self._redis = redis
        self._pubsub = redis.pubsub()
        self._shutdown = False
        
        # Subscribe to broadcast channel
        await self._pubsub.subscribe(BROADCAST_CHANNEL)
        
        # Start listener task
        self._listener_task = asyncio.create_task(self._pubsub_listener())
        
        logger.info("WebSocket ConnectionManager started")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the connection manager."""
        self._shutdown = True
        
        # Cancel listener task
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for user_id, connections in list(self._active_connections.items()):
            for websocket in list(connections):
                try:
                    await websocket.close(code=1001, reason="Server shutdown")
                except Exception:
                    pass
        
        self._active_connections.clear()
        
        # Close pubsub
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        
        logger.info("WebSocket ConnectionManager shutdown complete")
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    async def connect(self, websocket: WebSocket, user_id: int) -> None:
        """
        Accept and register a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            user_id: Authenticated user's ID
        """
        await websocket.accept()
        
        # Add to active connections
        if user_id not in self._active_connections:
            self._active_connections[user_id] = set()
        self._active_connections[user_id].add(websocket)
        
        # Subscribe to user-specific channel
        if self._pubsub:
            channel = f"{USER_CHANNEL_PREFIX}{user_id}"
            await self._pubsub.subscribe(channel)
        
        # Send welcome message
        await self._send_to_websocket(
            websocket,
            build_message(MessageType.CONNECTED, {"user_id": user_id}),
        )
        
        logger.info(
            f"WebSocket connected: user_id={user_id}, "
            f"total_connections={self.connection_count}"
        )
    
    async def disconnect(self, websocket: WebSocket, user_id: int) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            user_id: User's ID
        """
        if user_id in self._active_connections:
            self._active_connections[user_id].discard(websocket)
            
            # If no more connections for this user, unsubscribe from their channel
            if not self._active_connections[user_id]:
                del self._active_connections[user_id]
                
                if self._pubsub:
                    channel = f"{USER_CHANNEL_PREFIX}{user_id}"
                    await self._pubsub.unsubscribe(channel)
        
        logger.info(
            f"WebSocket disconnected: user_id={user_id}, "
            f"total_connections={self.connection_count}"
        )
    
    @property
    def connection_count(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self._active_connections.values())
    
    @property
    def user_count(self) -> int:
        """Get number of connected users."""
        return len(self._active_connections)
    
    def is_user_connected(self, user_id: int) -> bool:
        """Check if a user has any active connections."""
        return user_id in self._active_connections and bool(
            self._active_connections[user_id]
        )
    
    # =========================================================================
    # Message Sending
    # =========================================================================
    
    async def send_personal_message(
        self,
        user_id: int,
        message: dict[str, Any],
    ) -> bool:
        """
        Send a message to a specific user (all their connections).
        
        Uses Redis pub/sub for cross-instance delivery.
        
        Args:
            user_id: Target user's ID
            message: Message to send
            
        Returns:
            True if message was published successfully
        """
        if not self._redis:
            logger.warning("Redis not initialized, cannot send message")
            return False
        
        channel = f"{USER_CHANNEL_PREFIX}{user_id}"
        payload = json.dumps(message)
        
        try:
            await self._redis.publish(channel, payload)
            logger.debug(f"Published message to {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False
    
    async def broadcast(
        self,
        message: dict[str, Any],
        exclude_user: int | None = None,
    ) -> bool:
        """
        Broadcast a message to all connected users.
        
        Args:
            message: Message to broadcast
            exclude_user: Optional user ID to exclude from broadcast
            
        Returns:
            True if message was published successfully
        """
        if not self._redis:
            logger.warning("Redis not initialized, cannot broadcast")
            return False
        
        payload = json.dumps({
            "message": message,
            "exclude_user": exclude_user,
        })
        
        try:
            await self._redis.publish(BROADCAST_CHANNEL, payload)
            logger.debug("Published broadcast message")
            return True
        except Exception as e:
            logger.error(f"Failed to broadcast message: {e}")
            return False
    
    async def send_direct(
        self,
        websocket: WebSocket,
        message: dict[str, Any],
    ) -> bool:
        """
        Send a message directly to a specific WebSocket connection.
        
        Use this for responses to client messages (like pong).
        
        Args:
            websocket: Target WebSocket
            message: Message to send
            
        Returns:
            True if message was sent successfully
        """
        return await self._send_to_websocket(websocket, message)
    
    # =========================================================================
    # Internal: Message Delivery
    # =========================================================================
    
    async def _send_to_websocket(
        self,
        websocket: WebSocket,
        message: dict[str, Any],
    ) -> bool:
        """Send a message to a single WebSocket connection."""
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.debug(f"Failed to send to websocket: {e}")
            return False
    
    async def _deliver_to_user(
        self,
        user_id: int,
        message: dict[str, Any],
    ) -> int:
        """
        Deliver a message to all connections for a user (local instance only).
        
        Returns:
            Number of connections message was sent to
        """
        connections = self._active_connections.get(user_id, set())
        if not connections:
            return 0
        
        sent_count = 0
        dead_connections = []
        
        for websocket in connections:
            if await self._send_to_websocket(websocket, message):
                sent_count += 1
            else:
                dead_connections.append(websocket)
        
        # Clean up dead connections
        for websocket in dead_connections:
            connections.discard(websocket)
        
        return sent_count
    
    async def _deliver_broadcast(
        self,
        message: dict[str, Any],
        exclude_user: int | None = None,
    ) -> int:
        """
        Deliver a broadcast message to all local connections.
        
        Returns:
            Number of connections message was sent to
        """
        sent_count = 0
        
        for user_id, connections in self._active_connections.items():
            if exclude_user and user_id == exclude_user:
                continue
            
            for websocket in connections:
                if await self._send_to_websocket(websocket, message):
                    sent_count += 1
        
        return sent_count
    
    # =========================================================================
    # Internal: Pub/Sub Listener
    # =========================================================================
    
    async def _pubsub_listener(self) -> None:
        """
        Listen for messages from Redis pub/sub and deliver to local connections.
        
        This runs as a background task and handles messages from other instances.
        """
        if not self._pubsub:
            return
        
        logger.info("Pub/sub listener started")
        
        try:
            while not self._shutdown:
                try:
                    message = await self._pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=1.0,
                    )
                    
                    if message is None:
                        continue
                    
                    channel = message.get("channel")
                    data = message.get("data")
                    
                    if not isinstance(data, (str, bytes)):
                        continue
                    
                    # Decode if bytes
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    
                    # Decode if channel is bytes
                    if isinstance(channel, bytes):
                        channel = channel.decode("utf-8")
                    
                    await self._handle_pubsub_message(channel, data)
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Pub/sub listener error: {e}")
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info("Pub/sub listener cancelled")
            raise
    
    async def _handle_pubsub_message(self, channel: str, data: str) -> None:
        """Handle a message received from Redis pub/sub."""
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from pub/sub: {data[:100]}")
            return
        
        # Handle broadcast messages
        if channel == BROADCAST_CHANNEL:
            message = payload.get("message", {})
            exclude_user = payload.get("exclude_user")
            await self._deliver_broadcast(message, exclude_user)
            return
        
        # Handle user-specific messages
        if channel.startswith(USER_CHANNEL_PREFIX):
            user_id_str = channel[len(USER_CHANNEL_PREFIX):]
            try:
                user_id = int(user_id_str)
                await self._deliver_to_user(user_id, payload)
            except ValueError:
                logger.warning(f"Invalid user ID in channel: {channel}")


# =============================================================================
# Singleton Instance
# =============================================================================

# Global connection manager instance
connection_manager = ConnectionManager()

