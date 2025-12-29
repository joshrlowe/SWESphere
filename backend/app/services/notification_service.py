"""
Notification service.

Handles creation, retrieval, and management of user notifications.
Supports real-time delivery via Redis pub/sub.
"""

from typing import Any

from redis.asyncio import Redis
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_keys import redis_keys
from app.models.notification import Notification, NotificationType


class NotificationService:
    """Service for notification operations."""

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.db = db
        self.redis = redis

    # =========================================================================
    # Core CRUD Operations
    # =========================================================================

    async def create_notification(
        self,
        *,
        user_id: int,
        notification_type: NotificationType,
        data: dict[str, Any],
        actor_id: int | None = None,
    ) -> Notification:
        """
        Create and persist a new notification.
        
        Also publishes to Redis for real-time delivery.
        
        Args:
            user_id: Recipient user ID
            notification_type: Type of notification
            data: Additional payload data
            actor_id: User who triggered the notification (optional)
            
        Returns:
            Created Notification
        """
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            actor_id=actor_id,
        )
        notification.data = data
        
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)

        # Publish for real-time delivery
        await self._publish_notification(user_id, notification.id)

        return notification

    async def get_user_notifications(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 20,
        unread_only: bool = False,
    ) -> list[Notification]:
        """
        Get notifications for a user.
        
        Args:
            user_id: User to fetch notifications for
            skip: Number of records to skip (pagination)
            limit: Maximum records to return
            unread_only: If True, only return unread notifications
            
        Returns:
            List of Notification objects
        """
        query = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        if unread_only:
            query = query.where(Notification.read.is_(False))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read.is_(False),
            )
        )
        return result.scalar() or 0

    # =========================================================================
    # Read Status Management
    # =========================================================================

    async def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """
        Mark a single notification as read.
        
        Args:
            notification_id: Notification to mark
            user_id: Owner of the notification (for authorization)
            
        Returns:
            True if notification was found and updated
        """
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(read=True)
        )
        await self.db.flush()
        return result.rowcount > 0

    async def mark_all_as_read(self, user_id: int) -> int:
        """
        Mark all notifications as read for a user.
        
        Args:
            user_id: User whose notifications to mark
            
        Returns:
            Number of notifications marked as read
        """
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read.is_(False),
            )
            .values(read=True)
        )
        await self.db.flush()
        return result.rowcount

    # =========================================================================
    # Deletion
    # =========================================================================

    async def delete_notification(self, notification_id: int, user_id: int) -> bool:
        """
        Delete a notification.
        
        Args:
            notification_id: Notification to delete
            user_id: Owner of the notification (for authorization)
            
        Returns:
            True if notification was found and deleted
        """
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()

        if notification:
            await self.db.delete(notification)
            await self.db.flush()
            return True
        return False

    # =========================================================================
    # Notification Factory Methods
    # =========================================================================

    async def notify_new_follower(
        self,
        user_id: int,
        follower_id: int,
        follower_username: str,
    ) -> Notification:
        """Create notification for new follower event."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.NEW_FOLLOWER,
            data={"follower_username": follower_username},
            actor_id=follower_id,
        )

    async def notify_post_liked(
        self,
        user_id: int,
        liker_id: int,
        liker_username: str,
        post_id: int,
    ) -> Notification:
        """Create notification for post like event."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.POST_LIKED,
            data={"liker_username": liker_username, "post_id": post_id},
            actor_id=liker_id,
        )

    async def notify_new_comment(
        self,
        user_id: int,
        commenter_id: int,
        commenter_username: str,
        post_id: int,
    ) -> Notification:
        """Create notification for new comment event."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.POST_COMMENTED,
            data={"commenter_username": commenter_username, "post_id": post_id},
            actor_id=commenter_id,
        )

    async def notify_mention(
        self,
        user_id: int,
        mentioner_id: int,
        mentioner_username: str,
        post_id: int,
    ) -> Notification:
        """Create notification for mention event."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.MENTIONED,
            data={"mentioner_username": mentioner_username, "post_id": post_id},
            actor_id=mentioner_id,
        )

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    async def _publish_notification(self, user_id: int, notification_id: int) -> None:
        """Publish notification to Redis for real-time delivery."""
        channel = redis_keys.notification_channel(user_id)
        await self.redis.publish(channel, str(notification_id))
