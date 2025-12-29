"""
Cleanup and maintenance Celery tasks.

Handles periodic cleanup of:
- Expired tokens (hourly)
- Old notifications (daily)
- Soft-deleted records (weekly)
- Orphaned media files (daily)
- User statistics updates
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.redis_keys import redis_keys
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Default retention periods
DEFAULT_NOTIFICATION_RETENTION_DAYS = 90
DEFAULT_SOFT_DELETE_RETENTION_DAYS = 30


# =============================================================================
# Helper Functions
# =============================================================================

def _get_redis_client():
    """Get Redis client for cache operations."""
    from redis import Redis
    return Redis.from_url(str(settings.REDIS_URL), decode_responses=True)


def _get_sync_db_session():
    """Get synchronous database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    sync_url = settings.database_url_sync
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


# =============================================================================
# Token Cleanup (Hourly)
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.cleanup_tasks.cleanup_expired_tokens",
    bind=True,
)
def cleanup_expired_tokens(self) -> dict[str, Any]:
    """
    Clean up expired tokens from Redis.
    
    Runs hourly via Celery Beat.
    
    Note: Redis keys with TTL expire automatically, but this task:
    - Cleans up any orphaned keys without TTL
    - Provides visibility into token cleanup
    - Can be used for auditing
    
    Returns:
        Dict with cleanup stats
    """
    logger.info("Starting expired token cleanup")
    
    try:
        redis = _get_redis_client()
        cleaned_count = 0
        
        # Scan for blacklisted tokens (they should have TTL)
        pattern = redis_keys.token_blacklist_pattern()
        
        for key in redis.scan_iter(match=pattern, count=100):
            # Check if key has TTL
            ttl = redis.ttl(key)
            
            # TTL of -1 means no expiration (orphaned key)
            if ttl == -1:
                redis.delete(key)
                cleaned_count += 1
                logger.debug(f"Deleted orphaned token key: {key}")
            
            # TTL of -2 means key doesn't exist (already expired)
            # No action needed
        
        # Also clean up any orphaned session keys
        session_pattern = "session:*"
        for key in redis.scan_iter(match=session_pattern, count=100):
            ttl = redis.ttl(key)
            if ttl == -1:
                redis.delete(key)
                cleaned_count += 1
        
        logger.info(f"Token cleanup completed: {cleaned_count} orphaned keys removed")
        
        return {
            "status": "success",
            "cleaned_count": cleaned_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as exc:
        logger.error(f"Token cleanup failed: {exc}")
        return {
            "status": "error",
            "error": str(exc),
        }


# =============================================================================
# Notification Cleanup (Daily)
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.cleanup_tasks.cleanup_old_notifications",
    bind=True,
)
def cleanup_old_notifications(
    self,
    days: int = DEFAULT_NOTIFICATION_RETENTION_DAYS,
) -> dict[str, Any]:
    """
    Clean up old read notifications.
    
    Runs daily at 3 AM UTC via Celery Beat.
    
    Args:
        days: Delete read notifications older than this many days
        
    Returns:
        Dict with cleanup stats
    """
    from app.models.notification import Notification
    
    logger.info(f"Cleaning up read notifications older than {days} days")
    
    session = _get_sync_db_session()
    
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Delete read notifications older than cutoff
        deleted = (
            session.query(Notification)
            .filter(
                Notification.read == True,  # noqa: E712
                Notification.created_at < cutoff_date,
            )
            .delete(synchronize_session=False)
        )
        
        session.commit()
        
        logger.info(f"Notification cleanup completed: {deleted} notifications deleted")
        
        return {
            "status": "success",
            "deleted_count": deleted,
            "cutoff_date": cutoff_date.isoformat(),
        }
        
    except Exception as exc:
        session.rollback()
        logger.error(f"Notification cleanup failed: {exc}")
        return {
            "status": "error",
            "error": str(exc),
        }
    finally:
        session.close()


# =============================================================================
# Soft-Deleted Records Cleanup (Weekly)
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.cleanup_tasks.cleanup_soft_deleted_records",
    bind=True,
)
def cleanup_soft_deleted_records(
    self,
    days: int = DEFAULT_SOFT_DELETE_RETENTION_DAYS,
) -> dict[str, Any]:
    """
    Permanently delete soft-deleted records.
    
    Runs weekly on Sunday at 4 AM UTC via Celery Beat.
    
    This task hard-deletes records that have been soft-deleted for
    longer than the retention period, freeing up database space.
    
    Args:
        days: Delete records soft-deleted more than this many days ago
        
    Returns:
        Dict with cleanup stats per model
    """
    from app.models.post import Post
    from app.models.comment import Comment
    from app.models.user import User
    
    logger.info(f"Cleaning up soft-deleted records older than {days} days")
    
    session = _get_sync_db_session()
    results = {
        "status": "success",
        "deleted_by_model": {},
        "total_deleted": 0,
    }
    
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Models with soft delete support
        models_to_clean = [
            ("comments", Comment),
            ("posts", Post),
            # Users are typically not hard-deleted for data integrity
            # ("users", User),
        ]
        
        for model_name, model_class in models_to_clean:
            try:
                # Check if model has deleted_at column
                if not hasattr(model_class, "deleted_at"):
                    continue
                
                # Delete records where deleted_at is older than cutoff
                deleted = (
                    session.query(model_class)
                    .filter(
                        model_class.deleted_at.isnot(None),
                        model_class.deleted_at < cutoff_date,
                    )
                    .delete(synchronize_session=False)
                )
                
                results["deleted_by_model"][model_name] = deleted
                results["total_deleted"] += deleted
                
                logger.info(f"Deleted {deleted} soft-deleted {model_name}")
                
            except Exception as e:
                logger.error(f"Failed to clean {model_name}: {e}")
                results["deleted_by_model"][model_name] = f"error: {e}"
        
        session.commit()
        
        logger.info(f"Soft-delete cleanup completed: {results['total_deleted']} total records")
        
        return results
        
    except Exception as exc:
        session.rollback()
        logger.error(f"Soft-delete cleanup failed: {exc}")
        return {
            "status": "error",
            "error": str(exc),
        }
    finally:
        session.close()


# =============================================================================
# Orphaned Media Cleanup (Daily)
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.cleanup_tasks.cleanup_orphaned_media",
    bind=True,
)
def cleanup_orphaned_media(self) -> dict[str, Any]:
    """
    Clean up orphaned media files not referenced by any records.
    
    Runs daily at 5 AM UTC via Celery Beat.
    
    This task:
    1. Scans the uploads directory for media files
    2. Checks if each file is referenced in the database
    3. Deletes unreferenced files older than 24 hours
    
    Returns:
        Dict with cleanup stats
    """
    from app.models.user import User
    from app.models.post import Post
    
    logger.info("Starting orphaned media cleanup")
    
    session = _get_sync_db_session()
    upload_dir = Path(settings.UPLOAD_DIR)
    
    results = {
        "status": "success",
        "scanned_files": 0,
        "deleted_files": 0,
        "freed_bytes": 0,
        "errors": [],
    }
    
    try:
        # Get all referenced avatar paths
        avatars = session.query(User.avatar_custom).filter(
            User.avatar_custom.isnot(None)
        ).all()
        referenced_paths = {a[0] for a in avatars if a[0]}
        
        # TODO: Add post media references when implemented
        # post_media = session.query(Post.media_url).filter(
        #     Post.media_url.isnot(None)
        # ).all()
        # referenced_paths.update({m[0] for m in post_media if m[0]})
        
        # Cutoff for deletion (files must be at least 24 hours old)
        age_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Scan upload directories
        for subdir in ["avatars", "media"]:
            dir_path = upload_dir / subdir
            if not dir_path.exists():
                continue
            
            for file_path in dir_path.iterdir():
                if not file_path.is_file():
                    continue
                
                results["scanned_files"] += 1
                
                # Check file age
                file_mtime = datetime.fromtimestamp(
                    file_path.stat().st_mtime,
                    tz=timezone.utc,
                )
                
                if file_mtime > age_cutoff:
                    # File is too new, skip
                    continue
                
                # Check if file is referenced
                relative_path = str(file_path.relative_to(upload_dir))
                
                if relative_path not in referenced_paths:
                    try:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        results["deleted_files"] += 1
                        results["freed_bytes"] += file_size
                        logger.debug(f"Deleted orphaned file: {relative_path}")
                    except OSError as e:
                        results["errors"].append(f"{relative_path}: {e}")
        
        # Convert bytes to human readable
        freed_mb = results["freed_bytes"] / (1024 * 1024)
        
        logger.info(
            f"Media cleanup completed: {results['deleted_files']} files deleted, "
            f"{freed_mb:.2f} MB freed"
        )
        
        return results
        
    except Exception as exc:
        logger.error(f"Media cleanup failed: {exc}")
        return {
            "status": "error",
            "error": str(exc),
        }
    finally:
        session.close()


# =============================================================================
# User Statistics Update
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.cleanup_tasks.update_user_stats",
    bind=True,
)
def update_user_stats(self) -> dict[str, Any]:
    """
    Update cached user statistics.
    
    Runs every 15 minutes via Celery Beat.
    
    Recalculates and caches:
    - Follower/following counts
    - Post counts
    - Engagement metrics
    
    Returns:
        Dict with update stats
    """
    from sqlalchemy import func
    from app.models import followers
    from app.models.user import User
    from app.models.post import Post
    
    logger.info("Starting user stats update")
    
    session = _get_sync_db_session()
    redis = _get_redis_client()
    
    results = {
        "status": "success",
        "users_updated": 0,
        "errors": 0,
    }
    
    try:
        # Get all active users (posted or logged in recently)
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        
        active_users = (
            session.query(User)
            .filter(
                User.deleted_at.is_(None),
            )
            .all()
        )
        
        for user in active_users:
            try:
                # Calculate stats
                followers_count = (
                    session.query(func.count(followers.c.follower_id))
                    .filter(followers.c.followed_id == user.id)
                    .scalar()
                )
                
                following_count = (
                    session.query(func.count(followers.c.followed_id))
                    .filter(followers.c.follower_id == user.id)
                    .scalar()
                )
                
                posts_count = (
                    session.query(func.count(Post.id))
                    .filter(
                        Post.user_id == user.id,
                        Post.deleted_at.is_(None),
                    )
                    .scalar()
                )
                
                # Cache stats in Redis
                cache_key = redis_keys.cache("user_stats", str(user.id))
                redis.hset(cache_key, mapping={
                    "followers_count": followers_count,
                    "following_count": following_count,
                    "posts_count": posts_count,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                redis.expire(cache_key, 3600)  # 1 hour TTL
                
                results["users_updated"] += 1
                
            except Exception as e:
                logger.error(f"Failed to update stats for user {user.id}: {e}")
                results["errors"] += 1
        
        logger.info(
            f"User stats update completed: {results['users_updated']} users updated"
        )
        
        return results
        
    except Exception as exc:
        logger.error(f"User stats update failed: {exc}")
        return {
            "status": "error",
            "error": str(exc),
        }
    finally:
        session.close()


# =============================================================================
# Rate Limit Reset (Optional)
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.cleanup_tasks.reset_rate_limits",
    bind=True,
)
def reset_rate_limits(self, endpoint: str | None = None) -> dict[str, Any]:
    """
    Reset rate limit counters.
    
    Can be run manually for specific endpoints or all.
    
    Args:
        endpoint: Specific endpoint to reset, or None for all
        
    Returns:
        Dict with reset stats
    """
    logger.info(f"Resetting rate limits for: {endpoint or 'all endpoints'}")
    
    try:
        redis = _get_redis_client()
        
        if endpoint:
            pattern = redis_keys.rate_limit_pattern(endpoint)
        else:
            pattern = f"{redis_keys.RATE_LIMIT_PREFIX}:*"
        
        deleted_count = 0
        for key in redis.scan_iter(match=pattern, count=100):
            redis.delete(key)
            deleted_count += 1
        
        logger.info(f"Rate limit reset completed: {deleted_count} keys deleted")
        
        return {
            "status": "success",
            "endpoint": endpoint,
            "keys_deleted": deleted_count,
        }
        
    except Exception as exc:
        logger.error(f"Rate limit reset failed: {exc}")
        return {
            "status": "error",
            "error": str(exc),
        }

