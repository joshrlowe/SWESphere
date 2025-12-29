"""Celery application configuration."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "swesphere",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks.email", "app.workers.tasks.notifications"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result settings
    result_expires=3600,  # 1 hour
    # Rate limiting
    task_annotations={
        "app.workers.tasks.email.*": {"rate_limit": "10/m"},
    },
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-expired-tokens": {
            "task": "app.workers.tasks.cleanup.cleanup_expired_tokens",
            "schedule": 3600.0,  # Every hour
        },
        "send-notification-digest": {
            "task": "app.workers.tasks.notifications.send_daily_digest",
            "schedule": 86400.0,  # Every 24 hours
        },
    },
)


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f"Request: {self.request!r}")
