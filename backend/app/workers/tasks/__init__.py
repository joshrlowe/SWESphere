"""
Celery tasks package for SWESphere.

This package contains all background tasks organized by domain:
- email_tasks: Email sending (welcome, verification, password reset)
- notification_tasks: Push notifications, real-time publishing, digests
- feed_tasks: Trending feed generation, cache invalidation, fanout
- cleanup_tasks: Token cleanup, soft-delete pruning, media cleanup
"""

from app.workers.tasks.cleanup_tasks import (
    cleanup_expired_tokens,
    cleanup_old_notifications,
    cleanup_orphaned_media,
    cleanup_soft_deleted_records,
    reset_rate_limits,
    update_user_stats,
)
from app.workers.tasks.email_tasks import (
    send_email,
    send_notification_digest,
    send_password_reset_email,
    send_verification_email,
    send_welcome_email,
)
from app.workers.tasks.feed_tasks import (
    fanout_post_to_followers,
    generate_trending_feed,
    invalidate_user_feed_cache,
    precompute_user_feed,
)
from app.workers.tasks.notification_tasks import (
    broadcast_to_followers,
    create_notification_batch,
    process_mention,
    publish_realtime_notification,
    send_daily_digest,
    send_push_notification,
)

__all__ = [
    # Email tasks
    "send_email",
    "send_welcome_email",
    "send_verification_email",
    "send_password_reset_email",
    "send_notification_digest",
    # Notification tasks
    "create_notification_batch",
    "send_push_notification",
    "publish_realtime_notification",
    "send_daily_digest",
    "process_mention",
    "broadcast_to_followers",
    # Feed tasks
    "generate_trending_feed",
    "invalidate_user_feed_cache",
    "fanout_post_to_followers",
    "precompute_user_feed",
    # Cleanup tasks
    "cleanup_expired_tokens",
    "cleanup_old_notifications",
    "cleanup_soft_deleted_records",
    "cleanup_orphaned_media",
    "update_user_stats",
    "reset_rate_limits",
]
