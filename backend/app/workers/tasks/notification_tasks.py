"""
Notification-related Celery tasks.

Handles:
- Batch notification creation
- Push notifications (FCM/APNs)
- Real-time notification publishing (Redis pub/sub)
- Daily digest generation
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import settings
from app.core.redis_keys import redis_keys
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================

def _get_redis_client():
    """Get Redis client for pub/sub operations."""
    from redis import Redis
    return Redis.from_url(str(settings.REDIS_URL), decode_responses=True)


def _get_sync_db_session():
    """Get synchronous database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Use sync database URL for Celery (not async)
    sync_url = settings.database_url_sync
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


# =============================================================================
# Batch Notification Creation
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.notification_tasks.create_notification_batch",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def create_notification_batch(
    self,
    user_ids: list[int],
    notification_type: str,
    actor_id: int | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Create notifications for multiple users in a batch.
    
    Used for scenarios like:
    - Fanout notifications to followers
    - System announcements
    - Broadcast notifications
    
    Args:
        user_ids: List of user IDs to notify
        notification_type: Type of notification (e.g., "NEW_POST", "SYSTEM")
        actor_id: ID of the user who triggered the notification (optional)
        payload: JSON payload with notification data
        
    Returns:
        Dict with count of created notifications and any errors
    """
    from app.models.notification import Notification, NotificationType
    
    if not user_ids:
        return {"created": 0, "errors": 0, "message": "No users to notify"}
    
    # Filter out actor from recipients (don't notify self)
    if actor_id:
        user_ids = [uid for uid in user_ids if uid != actor_id]
    
    if not user_ids:
        return {"created": 0, "errors": 0, "message": "No users after filtering self"}
    
    logger.info(f"Creating batch notifications for {len(user_ids)} users: {notification_type}")
    
    session = _get_sync_db_session()
    created_count = 0
    error_count = 0
    
    try:
        # Convert string type to enum if needed
        try:
            notif_type = NotificationType(notification_type)
        except ValueError:
            notif_type = NotificationType.SYSTEM
        
        # Batch create notifications
        notifications = []
        for user_id in user_ids:
            notification = Notification(
                type=notif_type,
                user_id=user_id,
                actor_id=actor_id,
                payload_json=json.dumps(payload),
                read=False,
            )
            notifications.append(notification)
        
        # Bulk insert
        session.bulk_save_objects(notifications)
        session.commit()
        created_count = len(notifications)
        
        # Publish real-time notifications for each user
        for user_id in user_ids:
            publish_realtime_notification.delay(
                user_id=user_id,
                notification={
                    "type": notification_type,
                    "actor_id": actor_id,
                    "data": payload,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        
        logger.info(f"Batch notification complete: {created_count} created")
        
    except Exception as exc:
        session.rollback()
        error_count = len(user_ids)
        logger.error(f"Batch notification failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        session.close()
    
    return {
        "created": created_count,
        "errors": error_count,
        "notification_type": notification_type,
    }


# =============================================================================
# Push Notifications (FCM/APNs)
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.notification_tasks.send_push_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
)
def send_push_notification(
    self,
    user_id: int,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Send push notification to user's devices.
    
    Integrates with Firebase Cloud Messaging (FCM) for Android
    and Apple Push Notification Service (APNs) for iOS.
    
    Args:
        user_id: Target user ID
        title: Notification title
        body: Notification body text
        data: Additional data payload (for deep linking, etc.)
        
    Returns:
        Dict with delivery status per device
    """
    logger.info(f"Sending push notification to user {user_id}: {title}")
    
    # TODO: Implement actual push notification integration
    # 1. Fetch user's device tokens from database
    # 2. Determine token type (FCM vs APNs)
    # 3. Send to appropriate service
    
    # Placeholder implementation
    session = _get_sync_db_session()
    
    try:
        # Query user's device tokens
        # from app.models.device_token import DeviceToken
        # tokens = session.query(DeviceToken).filter_by(user_id=user_id).all()
        
        # For now, just log the notification
        notification_payload = {
            "user_id": user_id,
            "title": title,
            "body": body,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.info(f"Push notification payload: {notification_payload}")
        
        # FCM integration would look like:
        # import firebase_admin
        # from firebase_admin import messaging
        # 
        # for token in tokens:
        #     message = messaging.Message(
        #         notification=messaging.Notification(title=title, body=body),
        #         data=data,
        #         token=token.token,
        #     )
        #     messaging.send(message)
        
        return {
            "status": "sent",
            "user_id": user_id,
            "devices_count": 0,  # Placeholder
            "message": "Push notification queued (FCM integration pending)",
        }
        
    except Exception as exc:
        logger.error(f"Push notification failed for user {user_id}: {exc}")
        raise self.retry(exc=exc)
    finally:
        session.close()


# =============================================================================
# Real-time Notification Publishing (WebSocket/SSE via Redis)
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.notification_tasks.publish_realtime_notification",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def publish_realtime_notification(
    self,
    user_id: int,
    notification: dict[str, Any],
) -> dict[str, Any]:
    """
    Publish notification to Redis pub/sub for real-time delivery.
    
    Frontend clients subscribe to user-specific channels and receive
    notifications instantly via WebSocket or Server-Sent Events.
    
    Args:
        user_id: Target user ID
        notification: Notification data to publish
        
    Returns:
        Dict with publish status
    """
    logger.debug(f"Publishing realtime notification to user {user_id}")
    
    try:
        redis = _get_redis_client()
        
        # Get the channel name for this user
        channel = redis_keys.notification_channel(user_id)
        
        # Add metadata
        notification_with_meta = {
            **notification,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Publish to Redis channel
        message = json.dumps(notification_with_meta)
        subscribers = redis.publish(channel, message)
        
        # Also increment unread count cache
        count_key = redis_keys.notification_count(user_id)
        redis.incr(count_key)
        
        logger.debug(
            f"Published to channel {channel}, {subscribers} subscriber(s)"
        )
        
        return {
            "status": "published",
            "user_id": user_id,
            "channel": channel,
            "subscribers": subscribers,
        }
        
    except Exception as exc:
        logger.error(f"Failed to publish realtime notification: {exc}")
        raise self.retry(exc=exc)


# =============================================================================
# Daily Digest
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.notification_tasks.send_daily_digest",
    bind=True,
)
def send_daily_digest(self) -> dict[str, Any]:
    """
    Send daily notification digest to users.
    
    Queries users with unread notifications from the last 24 hours
    and sends a summary email.
    
    Returns:
        Dict with count of digests sent
    """
    from app.models.notification import Notification
    from app.models.user import User
    from app.workers.tasks.email_tasks import send_notification_digest
    
    logger.info("Starting daily digest task")
    
    session = _get_sync_db_session()
    sent_count = 0
    error_count = 0
    
    try:
        # Find users with unread notifications from last 24 hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Get distinct user IDs with unread notifications
        users_with_notifications = (
            session.query(User)
            .join(Notification, User.id == Notification.user_id)
            .filter(
                Notification.read == False,  # noqa: E712
                Notification.created_at >= cutoff,
            )
            .distinct()
            .all()
        )
        
        logger.info(f"Found {len(users_with_notifications)} users for digest")
        
        for user in users_with_notifications:
            try:
                # Get their unread notifications
                notifications = (
                    session.query(Notification)
                    .filter(
                        Notification.user_id == user.id,
                        Notification.read == False,  # noqa: E712
                        Notification.created_at >= cutoff,
                    )
                    .order_by(Notification.created_at.desc())
                    .limit(20)
                    .all()
                )
                
                if not notifications:
                    continue
                
                # Format notifications for email
                notif_summaries = []
                for notif in notifications:
                    notif_summaries.append({
                        "type": notif.type.value if hasattr(notif.type, "value") else str(notif.type),
                        "message": notif.get_message() if hasattr(notif, "get_message") else "",
                        "created_at": notif.created_at.isoformat(),
                    })
                
                # Queue digest email
                send_notification_digest.delay(
                    user_email=user.email,
                    username=user.username,
                    notifications=notif_summaries,
                )
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send digest to user {user.id}: {e}")
                error_count += 1
        
        logger.info(f"Daily digest completed: {sent_count} sent, {error_count} errors")
        
    except Exception as exc:
        logger.error(f"Daily digest task failed: {exc}")
        raise
    finally:
        session.close()
    
    return {
        "sent": sent_count,
        "errors": error_count,
    }


# =============================================================================
# Mention Processing
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.notification_tasks.process_mention",
    bind=True,
    max_retries=3,
)
def process_mention(
    self,
    post_id: int,
    author_id: int,
    mentioned_username: str,
) -> dict[str, Any]:
    """
    Process a mention in a post and create notification.
    
    Args:
        post_id: ID of the post containing the mention
        author_id: ID of the post author
        mentioned_username: Username that was mentioned
        
    Returns:
        Dict with processing status
    """
    from app.models.notification import Notification, NotificationType
    from app.models.user import User
    
    logger.info(f"Processing mention of @{mentioned_username} in post {post_id}")
    
    session = _get_sync_db_session()
    
    try:
        # Look up the mentioned user
        mentioned_user = session.query(User).filter_by(username=mentioned_username).first()
        
        if not mentioned_user:
            return {"status": "skipped", "reason": "user_not_found"}
        
        # Don't notify self
        if mentioned_user.id == author_id:
            return {"status": "skipped", "reason": "self_mention"}
        
        # Create notification
        notification = Notification(
            type=NotificationType.MENTIONED,
            user_id=mentioned_user.id,
            actor_id=author_id,
            payload_json=json.dumps({"post_id": post_id}),
            read=False,
        )
        session.add(notification)
        session.commit()
        
        # Publish realtime
        publish_realtime_notification.delay(
            user_id=mentioned_user.id,
            notification={
                "type": "MENTIONED",
                "actor_id": author_id,
                "data": {"post_id": post_id},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        
        # Send push notification
        author = session.query(User).get(author_id)
        author_name = author.username if author else "Someone"
        
        send_push_notification.delay(
            user_id=mentioned_user.id,
            title="You were mentioned!",
            body=f"@{author_name} mentioned you in a post",
            data={"post_id": post_id, "action": "view_post"},
        )
        
        return {"status": "success", "notification_id": notification.id}
        
    except Exception as exc:
        session.rollback()
        logger.error(f"Failed to process mention: {exc}")
        raise self.retry(exc=exc)
    finally:
        session.close()


# =============================================================================
# Broadcast to Followers
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.notification_tasks.broadcast_to_followers",
    bind=True,
)
def broadcast_to_followers(
    self,
    user_id: int,
    notification_type: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Broadcast a notification to all followers of a user.
    
    Args:
        user_id: ID of the user whose followers to notify
        notification_type: Type of notification
        data: Notification data
        
    Returns:
        Dict with broadcast results
    """
    from app.models import followers
    
    logger.info(f"Broadcasting {notification_type} to followers of user {user_id}")
    
    session = _get_sync_db_session()
    
    try:
        # Get all follower IDs
        from sqlalchemy import select
        
        result = session.execute(
            select(followers.c.follower_id).where(followers.c.followed_id == user_id)
        )
        follower_ids = [row[0] for row in result]
        
        if not follower_ids:
            return {"status": "no_followers", "count": 0}
        
        # Delegate to batch notification
        create_notification_batch.delay(
            user_ids=follower_ids,
            notification_type=notification_type,
            actor_id=user_id,
            payload=data,
        )
        
        return {
            "status": "queued",
            "follower_count": len(follower_ids),
            "notification_type": notification_type,
        }
        
    except Exception as exc:
        logger.error(f"Broadcast to followers failed: {exc}")
        raise
    finally:
        session.close()

