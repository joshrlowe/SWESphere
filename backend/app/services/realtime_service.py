"""
Real-time notification delivery service.

Provides high-level methods for sending real-time notifications
to connected WebSocket clients via the ConnectionManager.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.core.websocket import (
    MessageType,
    build_message,
    build_notification_message,
    build_unread_count_message,
    connection_manager,
)
from app.models.notification import Notification, NotificationType
from app.models.user import User

logger = logging.getLogger(__name__)


# =============================================================================
# Actor Serialization
# =============================================================================


def _serialize_actor(user: User) -> dict[str, Any]:
    """
    Serialize a user to actor format for notifications.
    
    Args:
        user: User model instance
        
    Returns:
        Actor dictionary with id, username, and avatar_url
    """
    return {
        "id": user.id,
        "username": user.username,
        "display_name": getattr(user, "display_name", None),
        "avatar_url": getattr(user, "avatar_url", None),
    }


def _notification_type_to_string(notification_type: NotificationType) -> str:
    """Convert NotificationType enum to string."""
    return notification_type.value.lower()


# =============================================================================
# Real-time Service
# =============================================================================


class RealtimeService:
    """
    Service for sending real-time notifications to connected clients.
    
    This service abstracts the WebSocket layer and provides a clean API
    for the rest of the application to send real-time updates.
    
    Usage:
        realtime = RealtimeService()
        
        # When a user follows another
        await realtime.notify_new_follower(
            user_id=followed_user.id,
            follower=follower_user,
            notification=notification,
        )
    """
    
    def __init__(self) -> None:
        """Initialize the realtime service."""
        self._manager = connection_manager
    
    # =========================================================================
    # Notification Methods
    # =========================================================================
    
    async def notify_new_follower(
        self,
        user_id: int,
        follower: User,
        notification: Notification | None = None,
    ) -> bool:
        """
        Send a new follower notification.
        
        Args:
            user_id: User being followed (recipient)
            follower: User who followed
            notification: Optional notification record
            
        Returns:
            True if message was published successfully
        """
        message = build_notification_message(
            notification_id=notification.id if notification else 0,
            notification_type="new_follower",
            message=f"@{follower.username} started following you",
            actor=_serialize_actor(follower),
        )
        
        return await self._send_to_user(user_id, message)
    
    async def notify_post_liked(
        self,
        user_id: int,
        liker: User,
        post_id: int,
        notification: Notification | None = None,
    ) -> bool:
        """
        Send a post liked notification.
        
        Args:
            user_id: Post author (recipient)
            liker: User who liked the post
            post_id: ID of the liked post
            notification: Optional notification record
            
        Returns:
            True if message was published successfully
        """
        message = build_notification_message(
            notification_id=notification.id if notification else 0,
            notification_type="post_liked",
            message=f"@{liker.username} liked your post",
            actor=_serialize_actor(liker),
            extra_data={"post_id": post_id},
        )
        
        return await self._send_to_user(user_id, message)
    
    async def notify_new_comment(
        self,
        user_id: int,
        commenter: User,
        post_id: int,
        comment_id: int,
        comment_preview: str | None = None,
        notification: Notification | None = None,
    ) -> bool:
        """
        Send a new comment notification.
        
        Args:
            user_id: Post author (recipient)
            commenter: User who commented
            post_id: ID of the post
            comment_id: ID of the new comment
            comment_preview: Optional preview of comment text
            notification: Optional notification record
            
        Returns:
            True if message was published successfully
        """
        message_text = f"@{commenter.username} commented on your post"
        if comment_preview:
            # Truncate long previews
            preview = comment_preview[:50]
            if len(comment_preview) > 50:
                preview += "..."
            message_text = f'@{commenter.username} commented: "{preview}"'
        
        message = build_notification_message(
            notification_id=notification.id if notification else 0,
            notification_type="new_comment",
            message=message_text,
            actor=_serialize_actor(commenter),
            extra_data={
                "post_id": post_id,
                "comment_id": comment_id,
            },
        )
        
        return await self._send_to_user(user_id, message)
    
    async def notify_mention(
        self,
        user_id: int,
        mentioner: User,
        post_id: int,
        notification: Notification | None = None,
    ) -> bool:
        """
        Send a mention notification.
        
        Args:
            user_id: Mentioned user (recipient)
            mentioner: User who mentioned them
            post_id: ID of the post with mention
            notification: Optional notification record
            
        Returns:
            True if message was published successfully
        """
        message = build_notification_message(
            notification_id=notification.id if notification else 0,
            notification_type="mention",
            message=f"@{mentioner.username} mentioned you in a post",
            actor=_serialize_actor(mentioner),
            extra_data={"post_id": post_id},
        )
        
        return await self._send_to_user(user_id, message)
    
    async def notify_reply(
        self,
        user_id: int,
        replier: User,
        post_id: int,
        reply_id: int,
        notification: Notification | None = None,
    ) -> bool:
        """
        Send a reply notification.
        
        Args:
            user_id: Original post author (recipient)
            replier: User who replied
            post_id: ID of original post
            reply_id: ID of the reply post
            notification: Optional notification record
            
        Returns:
            True if message was published successfully
        """
        message = build_notification_message(
            notification_id=notification.id if notification else 0,
            notification_type="reply",
            message=f"@{replier.username} replied to your post",
            actor=_serialize_actor(replier),
            extra_data={
                "post_id": post_id,
                "reply_id": reply_id,
            },
        )
        
        return await self._send_to_user(user_id, message)
    
    async def notify_system(
        self,
        user_id: int,
        title: str,
        body: str,
        notification: Notification | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send a system notification.
        
        Args:
            user_id: Recipient user
            title: Notification title
            body: Notification body
            notification: Optional notification record
            extra_data: Optional additional data
            
        Returns:
            True if message was published successfully
        """
        data = {
            "id": notification.id if notification else 0,
            "type": "system",
            "title": title,
            "message": body,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "read": False,
        }
        
        if extra_data:
            data.update(extra_data)
        
        message = build_message(MessageType.NOTIFICATION, data)
        return await self._send_to_user(user_id, message)
    
    # =========================================================================
    # Unread Count Updates
    # =========================================================================
    
    async def send_unread_count_update(
        self,
        user_id: int,
        count: int,
    ) -> bool:
        """
        Send an unread notification count update.
        
        Call this when notifications are marked as read or deleted.
        
        Args:
            user_id: User to update
            count: New unread count
            
        Returns:
            True if message was published successfully
        """
        message = build_unread_count_message(count)
        return await self._send_to_user(user_id, message)
    
    # =========================================================================
    # Batch Operations
    # =========================================================================
    
    async def notify_followers(
        self,
        follower_ids: list[int],
        notification_type: str,
        message_text: str,
        actor: User,
        extra_data: dict[str, Any] | None = None,
    ) -> int:
        """
        Send notifications to multiple users (e.g., all followers).
        
        Args:
            follower_ids: List of user IDs to notify
            notification_type: Type of notification
            message_text: Notification message
            actor: User who triggered the notification
            extra_data: Optional additional data
            
        Returns:
            Number of users notified
        """
        sent_count = 0
        
        for user_id in follower_ids:
            # Skip actor (don't notify yourself)
            if user_id == actor.id:
                continue
            
            message = build_notification_message(
                notification_id=0,  # Batch notifications don't have individual IDs
                notification_type=notification_type,
                message=message_text,
                actor=_serialize_actor(actor),
                extra_data=extra_data,
            )
            
            if await self._send_to_user(user_id, message):
                sent_count += 1
        
        return sent_count
    
    # =========================================================================
    # Broadcast
    # =========================================================================
    
    async def broadcast_announcement(
        self,
        title: str,
        body: str,
        exclude_user: int | None = None,
    ) -> bool:
        """
        Broadcast a system announcement to all connected users.
        
        Args:
            title: Announcement title
            body: Announcement body
            exclude_user: Optional user to exclude from broadcast
            
        Returns:
            True if message was published successfully
        """
        message = build_message(
            MessageType.NOTIFICATION,
            {
                "id": 0,
                "type": "announcement",
                "title": title,
                "message": body,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "read": False,
            },
        )
        
        return await self._manager.broadcast(message, exclude_user=exclude_user)
    
    # =========================================================================
    # Connection Status
    # =========================================================================
    
    def is_user_online(self, user_id: int) -> bool:
        """
        Check if a user has any active WebSocket connections.
        
        Args:
            user_id: User to check
            
        Returns:
            True if user has at least one active connection
        """
        return self._manager.is_user_connected(user_id)
    
    @property
    def online_user_count(self) -> int:
        """Get the number of users with active connections."""
        return self._manager.user_count
    
    @property
    def total_connections(self) -> int:
        """Get the total number of active WebSocket connections."""
        return self._manager.connection_count
    
    # =========================================================================
    # Internal
    # =========================================================================
    
    async def _send_to_user(
        self,
        user_id: int,
        message: dict[str, Any],
    ) -> bool:
        """Send a message to a user via the connection manager."""
        return await self._manager.send_personal_message(user_id, message)


# =============================================================================
# Singleton Instance
# =============================================================================

# Global realtime service instance
realtime_service = RealtimeService()

