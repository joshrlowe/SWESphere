"""
Notification service.

Handles creation, retrieval, and management of user notifications.
Supports real-time delivery via Redis pub/sub.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginatedResult, calculate_skip
from app.core.redis_keys import redis_keys
from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)


# =============================================================================
# Extended Pagination for Notifications
# =============================================================================


@dataclass
class PaginatedNotifications(PaginatedResult[Notification]):
    """
    Paginated notifications with unread count.
    
    Extends PaginatedResult to include the unread_count field
    specific to notifications.
    """
    
    unread_count: int = 0
    
    @classmethod
    def create_with_unread(
        cls,
        items: list[Notification],
        total: int,
        page: int,
        per_page: int,
        unread_count: int,
    ) -> "PaginatedNotifications":
        """Create paginated notifications with unread count."""
        from app.core.pagination import calculate_pages, has_next_page, has_prev_page
        
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=calculate_pages(total, per_page),
            has_next=has_next_page(page, per_page, total),
            has_prev=has_prev_page(page),
            unread_count=unread_count,
        )


# =============================================================================
# Service
# =============================================================================


class NotificationService:
    """
    Service for notification operations.

    Handles:
    - Creating notifications for various events
    - Fetching and paginating notifications
    - Marking as read (single and batch)
    - Real-time delivery via Redis pub/sub
    - Self-notification prevention
    """

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        """
        Initialize notification service.

        Args:
            db: Async database session
            redis: Redis client for real-time delivery
        """
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
    ) -> Notification | None:
        """
        Create and persist a new notification.

        Also publishes to Redis for real-time delivery.
        Prevents self-notifications (when actor_id == user_id).

        Args:
            user_id: Recipient user ID
            notification_type: Type of notification
            data: Additional payload data
            actor_id: User who triggered the notification (optional)

        Returns:
            Created Notification, or None if self-notification
        """
        # Prevent self-notifications
        if actor_id is not None and actor_id == user_id:
            logger.debug(f"Skipping self-notification for user {user_id}")
            return None

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
        await self._publish_notification(user_id, notification)

        # Increment unread count in cache
        await self._increment_unread_count(user_id)

        logger.info(
            f"Notification created: {notification_type.value} for user {user_id}"
        )
        return notification

    async def get_notifications(
        self,
        user_id: int,
        *,
        page: int = 1,
        per_page: int = 20,
        unread_only: bool = False,
    ) -> PaginatedNotifications:
        """
        Get notifications for a user with pagination.

        Args:
            user_id: User to fetch notifications for
            page: Page number (1-indexed)
            per_page: Items per page
            unread_only: If True, only return unread notifications

        Returns:
            PaginatedNotifications with notifications and metadata
        """
        skip = calculate_skip(page, per_page)

        # Build base query
        base_query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            base_query = base_query.where(Notification.read.is_(False))

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Get paginated results
        query = (
            base_query.order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(per_page)
        )

        result = await self.db.execute(query)
        notifications = list(result.scalars().all())

        # Get unread count
        unread_count = await self.get_unread_count(user_id)

        return PaginatedNotifications.create_with_unread(
            items=notifications,
            total=total,
            page=page,
            per_page=per_page,
            unread_count=unread_count,
        )

    async def get_unread_count(self, user_id: int) -> int:
        """
        Get count of unread notifications for a user.

        Checks cache first for performance.

        Args:
            user_id: User to count for

        Returns:
            Number of unread notifications
        """
        # Try cache first
        cache_key = redis_keys.notification_count(user_id)
        try:
            cached = await self.redis.get(cache_key)
            if cached is not None:
                return int(cached)
        except Exception as e:
            logger.warning(f"Cache error: {e}")

        # Query database
        result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read.is_(False),
            )
        )
        count = result.scalar() or 0

        # Update cache
        try:
            await self.redis.setex(cache_key, 300, str(count))  # 5 min TTL
        except Exception as e:
            logger.warning(f"Cache error: {e}")

        return count

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
                Notification.read.is_(False),  # Only update if unread
            )
            .values(read=True)
        )
        await self.db.flush()

        if result.rowcount > 0:
            await self._decrement_unread_count(user_id)
            logger.debug(f"Notification {notification_id} marked as read")
            return True

        return False

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

        count = result.rowcount
        if count > 0:
            # Reset cached count
            await self._reset_unread_count(user_id)
            logger.info(f"Marked {count} notifications as read for user {user_id}")

        return count

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
        # First check if it exists and is unread
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()

        if notification:
            was_unread = not notification.read
            await self.db.delete(notification)
            await self.db.flush()

            if was_unread:
                await self._decrement_unread_count(user_id)

            logger.debug(f"Notification {notification_id} deleted")
            return True

        return False

    async def delete_all_read(self, user_id: int) -> int:
        """
        Delete all read notifications for a user.

        Args:
            user_id: User whose read notifications to delete

        Returns:
            Number of notifications deleted
        """
        result = await self.db.execute(
            delete(Notification).where(
                Notification.user_id == user_id,
                Notification.read.is_(True),
            )
        )
        await self.db.flush()

        count = result.rowcount
        logger.info(f"Deleted {count} read notifications for user {user_id}")
        return count

    # =========================================================================
    # Notification Factory Methods
    # =========================================================================

    async def notify_new_follower(
        self,
        user_id: int,
        follower_id: int,
        follower_username: str,
    ) -> Notification | None:
        """Create notification for new follower event."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.NEW_FOLLOWER,
            data={
                "follower_id": follower_id,
                "follower_username": follower_username,
            },
            actor_id=follower_id,
        )

    async def notify_post_liked(
        self,
        user_id: int,
        liker_id: int,
        liker_username: str,
        post_id: int,
    ) -> Notification | None:
        """Create notification for post like event."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.POST_LIKED,
            data={
                "liker_id": liker_id,
                "liker_username": liker_username,
                "post_id": post_id,
            },
            actor_id=liker_id,
        )

    async def notify_new_comment(
        self,
        user_id: int,
        commenter_id: int,
        commenter_username: str,
        post_id: int,
        comment_id: int,
    ) -> Notification | None:
        """Create notification for new comment event."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.POST_COMMENTED,
            data={
                "commenter_id": commenter_id,
                "commenter_username": commenter_username,
                "post_id": post_id,
                "comment_id": comment_id,
            },
            actor_id=commenter_id,
        )

    async def notify_mention(
        self,
        user_id: int,
        mentioner_id: int,
        mentioner_username: str,
        post_id: int,
    ) -> Notification | None:
        """Create notification for mention event."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.MENTIONED,
            data={
                "mentioner_id": mentioner_id,
                "mentioner_username": mentioner_username,
                "post_id": post_id,
            },
            actor_id=mentioner_id,
        )

    async def notify_reply(
        self,
        user_id: int,
        replier_id: int,
        replier_username: str,
        post_id: int,
        reply_id: int,
    ) -> Notification | None:
        """Create notification for reply event."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.REPLY,
            data={
                "replier_id": replier_id,
                "replier_username": replier_username,
                "post_id": post_id,
                "reply_id": reply_id,
            },
            actor_id=replier_id,
        )

    async def notify_system(
        self,
        user_id: int,
        message: str,
    ) -> Notification | None:
        """Create a system notification."""
        return await self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.SYSTEM,
            data={"message": message},
            actor_id=None,
        )

    # =========================================================================
    # Real-time Delivery
    # =========================================================================

    async def _publish_notification(
        self,
        user_id: int,
        notification: Notification,
    ) -> None:
        """
        Publish notification to Redis for real-time delivery.

        Clients subscribe to their notification channel and receive
        updates in real-time via WebSocket or SSE.
        """
        try:
            channel = redis_keys.notification_channel(user_id)

            # Publish notification summary
            payload = json.dumps(
                {
                    "id": notification.id,
                    "type": notification.type.value,
                    "message": notification.message,
                    "actor_id": notification.actor_id,
                    "created_at": (
                        notification.created_at.isoformat()
                        if notification.created_at
                        else None
                    ),
                }
            )

            await self.redis.publish(channel, payload)
            logger.debug(f"Published notification to channel {channel}")

        except Exception as e:
            # Don't fail the notification creation if publish fails
            logger.error(f"Failed to publish notification: {e}")

    # =========================================================================
    # Cache Management
    # =========================================================================

    async def _increment_unread_count(self, user_id: int) -> None:
        """Increment cached unread count."""
        try:
            cache_key = redis_keys.notification_count(user_id)
            await self.redis.incr(cache_key)
        except Exception as e:
            logger.warning(f"Cache increment error: {e}")

    async def _decrement_unread_count(self, user_id: int) -> None:
        """Decrement cached unread count."""
        try:
            cache_key = redis_keys.notification_count(user_id)
            # Use decr but ensure we don't go below 0
            current = await self.redis.get(cache_key)
            if current and int(current) > 0:
                await self.redis.decr(cache_key)
        except Exception as e:
            logger.warning(f"Cache decrement error: {e}")

    async def _reset_unread_count(self, user_id: int) -> None:
        """Reset cached unread count to 0."""
        try:
            cache_key = redis_keys.notification_count(user_id)
            await self.redis.set(cache_key, "0")
        except Exception as e:
            logger.warning(f"Cache reset error: {e}")
