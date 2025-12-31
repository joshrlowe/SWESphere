"""
Celery application configuration for SWESphere.

This module configures Celery for background task processing including:
- Email notifications
- Push notifications
- Feed generation and caching
- Periodic cleanup tasks
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from app.config import settings

# =============================================================================
# Celery App Initialization
# =============================================================================

celery_app = Celery(
    "swesphere",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# =============================================================================
# Task Discovery
# =============================================================================

celery_app.autodiscover_tasks([
    "app.workers.tasks.email_tasks",
    "app.workers.tasks.notification_tasks",
    "app.workers.tasks.feed_tasks",
    "app.workers.tasks.cleanup_tasks",
    "app.workers.tasks.recommendation_tasks",
])

# =============================================================================
# Serialization Configuration
# =============================================================================

celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
)

# =============================================================================
# Task Execution Settings
# =============================================================================

celery_app.conf.update(
    # Acknowledge tasks after execution (safer)
    task_acks_late=True,
    
    # Reject tasks if worker crashes
    task_reject_on_worker_lost=True,
    
    # Track task state
    task_track_started=True,
    
    # Task time limits (seconds)
    task_time_limit=300,  # Hard limit: 5 minutes
    task_soft_time_limit=240,  # Soft limit: 4 minutes (raises exception)
    
    # Prefetch multiplier (how many tasks to prefetch)
    worker_prefetch_multiplier=4,
    
    # Concurrency (can be overridden by -c flag)
    worker_concurrency=4,
)

# =============================================================================
# Result Backend Settings
# =============================================================================

celery_app.conf.update(
    # Results expire after 1 hour
    result_expires=3600,
    
    # Compression
    result_compression="gzip",
    
    # Don't store results for tasks that don't need them
    task_ignore_result=False,
)

# =============================================================================
# Retry Configuration (Global Defaults)
# =============================================================================

celery_app.conf.update(
    # Default retry policy
    task_default_retry_delay=60,  # 1 minute
    
    # Exponential backoff settings (used by individual tasks)
    # Formula: delay * (2 ^ retry_count)
)

# =============================================================================
# Rate Limiting
# =============================================================================

celery_app.conf.update(
    task_annotations={
        # Email tasks: max 10 per minute (to avoid SMTP throttling)
        "app.workers.tasks.email_tasks.send_email": {
            "rate_limit": "10/m",
        },
        "app.workers.tasks.email_tasks.send_welcome_email": {
            "rate_limit": "10/m",
        },
        "app.workers.tasks.email_tasks.send_verification_email": {
            "rate_limit": "10/m",
        },
        "app.workers.tasks.email_tasks.send_password_reset_email": {
            "rate_limit": "10/m",
        },
        # Push notifications: max 100 per second
        "app.workers.tasks.notification_tasks.send_push_notification": {
            "rate_limit": "100/s",
        },
    },
)

# =============================================================================
# Queue Configuration
# =============================================================================

default_exchange = Exchange("default", type="direct")
priority_exchange = Exchange("priority", type="direct")

celery_app.conf.update(
    task_queues=(
        # Default queue for most tasks
        Queue("default", default_exchange, routing_key="default"),
        
        # High priority queue for real-time notifications
        Queue("high_priority", priority_exchange, routing_key="high"),
        
        # Low priority queue for cleanup and batch tasks
        Queue("low_priority", priority_exchange, routing_key="low"),
        
        # Dedicated queue for email (rate limited)
        Queue("email", default_exchange, routing_key="email"),
        
        # Dedicated queue for feed generation
        Queue("feed", default_exchange, routing_key="feed"),
    ),
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    
    # Route specific tasks to specific queues
    task_routes={
        # Email tasks go to email queue
        "app.workers.tasks.email_tasks.*": {"queue": "email"},
        
        # Real-time notifications go to high priority
        "app.workers.tasks.notification_tasks.publish_realtime_notification": {
            "queue": "high_priority",
        },
        
        # Feed generation tasks
        "app.workers.tasks.feed_tasks.*": {"queue": "feed"},
        
        # Recommendation tasks go to feed queue
        "app.workers.tasks.recommendation_tasks.*": {"queue": "feed"},
        
        # Cleanup tasks go to low priority
        "app.workers.tasks.cleanup_tasks.*": {"queue": "low_priority"},
    },
)

# =============================================================================
# Beat Schedule (Periodic Tasks)
# =============================================================================

celery_app.conf.beat_schedule = {
    # ---------------------------------
    # Feed Generation
    # ---------------------------------
    "generate-trending-feed": {
        "task": "app.workers.tasks.feed_tasks.generate_trending_feed",
        "schedule": 300.0,  # Every 5 minutes
        "options": {"queue": "feed"},
    },
    
    # ---------------------------------
    # Recommendation System
    # ---------------------------------
    "precompute-ranked-feeds": {
        "task": "app.workers.tasks.recommendation_tasks.precompute_feeds",
        "schedule": 180.0,  # Every 3 minutes
        "options": {"queue": "feed"},
    },
    "decay-affinity-scores": {
        "task": "app.workers.tasks.recommendation_tasks.decay_affinity_scores",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM UTC
        "options": {"queue": "low_priority"},
    },
    
    # ---------------------------------
    # Token Cleanup (Hourly)
    # ---------------------------------
    "cleanup-expired-tokens": {
        "task": "app.workers.tasks.cleanup_tasks.cleanup_expired_tokens",
        "schedule": 3600.0,  # Every hour
        "options": {"queue": "low_priority"},
    },
    
    # ---------------------------------
    # Notification Cleanup (Daily at 3 AM UTC)
    # ---------------------------------
    "cleanup-old-notifications": {
        "task": "app.workers.tasks.cleanup_tasks.cleanup_old_notifications",
        "schedule": crontab(hour=3, minute=0),
        "args": (90,),  # Delete notifications older than 90 days
        "options": {"queue": "low_priority"},
    },
    
    # ---------------------------------
    # Soft-Deleted Records (Weekly on Sunday at 4 AM UTC)
    # ---------------------------------
    "cleanup-soft-deleted-records": {
        "task": "app.workers.tasks.cleanup_tasks.cleanup_soft_deleted_records",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
        "args": (30,),  # Delete records soft-deleted more than 30 days ago
        "options": {"queue": "low_priority"},
    },
    
    # ---------------------------------
    # User Stats Update (Every 15 minutes)
    # ---------------------------------
    "update-user-stats": {
        "task": "app.workers.tasks.cleanup_tasks.update_user_stats",
        "schedule": 900.0,  # Every 15 minutes
        "options": {"queue": "low_priority"},
    },
    
    # ---------------------------------
    # Orphaned Media Cleanup (Daily at 5 AM UTC)
    # ---------------------------------
    "cleanup-orphaned-media": {
        "task": "app.workers.tasks.cleanup_tasks.cleanup_orphaned_media",
        "schedule": crontab(hour=5, minute=0),
        "options": {"queue": "low_priority"},
    },
    
    # ---------------------------------
    # Daily Digest (Daily at 8 AM UTC)
    # ---------------------------------
    "send-notification-digest": {
        "task": "app.workers.tasks.notification_tasks.send_daily_digest",
        "schedule": crontab(hour=8, minute=0),
        "options": {"queue": "email"},
    },
}

# =============================================================================
# Error Handling
# =============================================================================

celery_app.conf.update(
    # Send task-related events
    task_send_sent_event=True,
    
    # Worker events
    worker_send_task_events=True,
)


# =============================================================================
# Debug Task
# =============================================================================

@celery_app.task(bind=True, name="app.workers.celery_app.debug_task")
def debug_task(self):
    """Debug task for testing Celery configuration."""
    return {
        "request": str(self.request),
        "broker": settings.CELERY_BROKER_URL,
        "backend": settings.CELERY_RESULT_BACKEND,
    }
