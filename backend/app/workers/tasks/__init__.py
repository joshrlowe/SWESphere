"""
Celery tasks package for SWESphere.

This package contains all background tasks organized by domain:
- email_tasks: Email sending (welcome, verification, password reset)
- notification_tasks: Push notifications, real-time publishing, digests
- feed_tasks: Trending feed generation, cache invalidation, fanout
- cleanup_tasks: Token cleanup, soft-delete pruning, media cleanup
- recommendation_tasks: Ranked feed precomputation, affinity decay
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
from app.workers.tasks.recommendation_tasks import (
    compute_user_feed,
    decay_affinity_scores,
    invalidate_ranked_feed,
    precompute_feeds,
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
    # Recommendation tasks
    "precompute_feeds",
    "decay_affinity_scores",
    "compute_user_feed",
    "invalidate_ranked_feed",
    # Cleanup tasks
    "cleanup_expired_tokens",
    "cleanup_old_notifications",
    "cleanup_soft_deleted_records",
    "cleanup_orphaned_media",
    "update_user_stats",
    "reset_rate_limits",
]
