"""
WebSocket endpoints for real-time notifications.

Provides bidirectional communication for:
- Receiving real-time notifications
- Updating unread counts
- Mark notifications as read
- Connection health via ping/pong
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_access_token
from app.core.websocket import (
    MessageType,
    build_message,
    build_unread_count_message,
    connection_manager,
)
from app.db.session import async_session_factory
from app.models.user import User
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# WebSocket Authentication
# =============================================================================


async def authenticate_websocket(token: str, db: AsyncSession) -> User | None:
    """
    Authenticate a WebSocket connection via JWT token.
    
    Args:
        token: JWT access token
        db: Database session
        
    Returns:
        Authenticated User or None if authentication fails
    """
    # Verify token
    user_id = verify_access_token(token)
    if not user_id:
        logger.warning("WebSocket auth failed: invalid token")
        return None
    
    # Fetch user
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.warning(f"WebSocket auth failed: user {user_id} not found")
        return None
    
    if not user.is_active:
        logger.warning(f"WebSocket auth failed: user {user_id} is inactive")
        return None
    
    return user


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    """
    WebSocket endpoint for real-time notifications.
    
    ## Connection
    Connect with a valid JWT token as a query parameter:
    ```
    ws://host/api/v1/ws/notifications?token=your_jwt_token
    ```
    
    ## Messages from Server
    
    ### notification
    ```json
    {
      "type": "notification",
      "data": {
        "id": 123,
        "type": "new_follower",
        "message": "John started following you",
        "timestamp": "2024-01-15T10:30:00Z",
        "actor": {"id": 1, "username": "john", "avatar_url": "..."},
        "read": false
      },
      "timestamp": "2024-01-15T10:30:00Z"
    }
    ```
    
    ### unread_count
    ```json
    {
      "type": "unread_count",
      "data": {"count": 5},
      "timestamp": "2024-01-15T10:30:00Z"
    }
    ```
    
    ### pong (response to ping)
    ```json
    {
      "type": "pong",
      "data": {},
      "timestamp": "2024-01-15T10:30:00Z"
    }
    ```
    
    ## Messages from Client
    
    ### ping (keepalive)
    ```json
    {"type": "ping"}
    ```
    
    ### mark_read (mark notification as read)
    ```json
    {"type": "mark_read", "notification_id": 123}
    ```
    
    ### mark_all_read
    ```json
    {"type": "mark_all_read"}
    ```
    """
    # Get database session
    async with async_session_factory() as db:
        # Authenticate
        user = await authenticate_websocket(token, db)
        if not user:
            await websocket.close(code=4001, reason="Authentication failed")
            return
        
        user_id = user.id
        username = user.username
    
    # Connect to manager
    await connection_manager.connect(websocket, user_id)
    logger.info(f"WebSocket opened for user: {username} (id={user_id})")
    
    try:
        # Send initial unread count
        await _send_initial_unread_count(websocket, user_id)
        
        # Main message loop
        while True:
            try:
                # Wait for message with timeout (for keepalive)
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=60.0,  # 60 second timeout
                )
                
                await _handle_client_message(websocket, user_id, message)
                
            except asyncio.TimeoutError:
                # Send ping on timeout to keep connection alive
                await connection_manager.send_direct(
                    websocket,
                    build_message(MessageType.PING),
                )
                
    except WebSocketDisconnect as e:
        logger.info(f"WebSocket closed for user {username}: code={e.code}")
    except Exception as e:
        logger.error(f"WebSocket error for user {username}: {e}")
    finally:
        await connection_manager.disconnect(websocket, user_id)


# =============================================================================
# Message Handlers
# =============================================================================


async def _send_initial_unread_count(websocket: WebSocket, user_id: int) -> None:
    """Send the initial unread notification count to a newly connected client."""
    try:
        async with async_session_factory() as db:
            from app.dependencies import get_redis
            redis = await get_redis()
            
            notification_service = NotificationService(db, redis)
            count = await notification_service.get_unread_count(user_id)
            
            await connection_manager.send_direct(
                websocket,
                build_unread_count_message(count),
            )
    except Exception as e:
        logger.error(f"Failed to send initial unread count: {e}")


async def _handle_client_message(
    websocket: WebSocket,
    user_id: int,
    message: dict[str, Any],
) -> None:
    """
    Handle a message received from the client.
    
    Args:
        websocket: Client's WebSocket connection
        user_id: Authenticated user's ID
        message: Parsed message from client
    """
    msg_type = message.get("type")
    
    if msg_type == MessageType.PING:
        # Respond with pong
        await connection_manager.send_direct(
            websocket,
            build_message(MessageType.PONG),
        )
        
    elif msg_type == MessageType.MARK_READ:
        # Mark a single notification as read
        notification_id = message.get("notification_id")
        if notification_id:
            await _handle_mark_read(websocket, user_id, notification_id)
        else:
            await _send_error(websocket, "notification_id is required")
            
    elif msg_type == "mark_all_read":
        # Mark all notifications as read
        await _handle_mark_all_read(websocket, user_id)
        
    else:
        await _send_error(websocket, f"Unknown message type: {msg_type}")


async def _handle_mark_read(
    websocket: WebSocket,
    user_id: int,
    notification_id: int,
) -> None:
    """Handle marking a notification as read."""
    try:
        async with async_session_factory() as db:
            from app.dependencies import get_redis
            redis = await get_redis()
            
            notification_service = NotificationService(db, redis)
            success = await notification_service.mark_as_read(notification_id, user_id)
            await db.commit()
            
            if success:
                # Send updated unread count
                count = await notification_service.get_unread_count(user_id)
                await connection_manager.send_direct(
                    websocket,
                    build_unread_count_message(count),
                )
            else:
                await _send_error(
                    websocket,
                    "Notification not found or already read",
                )
                
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        await _send_error(websocket, "Failed to mark notification as read")


async def _handle_mark_all_read(websocket: WebSocket, user_id: int) -> None:
    """Handle marking all notifications as read."""
    try:
        async with async_session_factory() as db:
            from app.dependencies import get_redis
            redis = await get_redis()
            
            notification_service = NotificationService(db, redis)
            count = await notification_service.mark_all_as_read(user_id)
            await db.commit()
            
            # Send updated unread count (should be 0)
            await connection_manager.send_direct(
                websocket,
                build_unread_count_message(0),
            )
            
            logger.info(f"User {user_id} marked {count} notifications as read via WS")
            
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        await _send_error(websocket, "Failed to mark all notifications as read")


async def _send_error(websocket: WebSocket, message: str) -> None:
    """Send an error message to the client."""
    await connection_manager.send_direct(
        websocket,
        build_message(MessageType.ERROR, {"message": message}),
    )


# =============================================================================
# Health Check Endpoint
# =============================================================================


@router.get("/ws/stats")
async def websocket_stats() -> dict[str, Any]:
    """
    Get WebSocket connection statistics.
    
    Useful for monitoring and debugging.
    """
    return {
        "total_connections": connection_manager.connection_count,
        "connected_users": connection_manager.user_count,
    }

