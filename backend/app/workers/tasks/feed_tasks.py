"""
Feed generation and caching Celery tasks.

Handles:
- Trending/explore feed generation
- User feed cache invalidation
- Post fanout to followers
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
# Constants
# =============================================================================

# Feed cache TTL in seconds
TRENDING_FEED_TTL = 300  # 5 minutes
HOME_FEED_TTL = 180  # 3 minutes

# Trending algorithm parameters
TRENDING_WINDOW_HOURS = 24
TRENDING_LIKE_WEIGHT = 1.0
TRENDING_COMMENT_WEIGHT = 2.0
TRENDING_RECENCY_DECAY = 0.95


# =============================================================================
# Helper Functions
# =============================================================================

def _get_redis_client():
    """Get Redis client for caching operations."""
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


def _serialize_post_for_cache(post) -> dict[str, Any]:
    """Serialize a Post model to a cacheable dict."""
    return {
        "id": post.id,
        "body": post.body,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "likes_count": post.likes_count or 0,
        "comments_count": post.comments_count or 0,
        "author": {
            "id": post.author.id,
            "username": post.author.username,
            "avatar_url": post.author.avatar_url if hasattr(post.author, "avatar_url") else None,
        } if post.author else None,
    }


# =============================================================================
# Trending Feed Generation
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.feed_tasks.generate_trending_feed",
    bind=True,
)
def generate_trending_feed(self) -> dict[str, Any]:
    """
    Generate and cache the trending/explore feed.
    
    Uses a scoring algorithm based on:
    - Likes (weighted)
    - Comments (weighted higher)
    - Recency (exponential decay)
    
    Runs every 5 minutes via Celery Beat.
    
    Returns:
        Dict with generation stats
    """
    from sqlalchemy import desc, func
    from app.models.post import Post
    from app.models.user import User
    
    logger.info("Generating trending feed")
    start_time = datetime.now(timezone.utc)
    
    session = _get_sync_db_session()
    redis = _get_redis_client()
    
    try:
        # Calculate cutoff for recency
        cutoff = datetime.now(timezone.utc) - timedelta(hours=TRENDING_WINDOW_HOURS)
        
        # Query posts with engagement metrics
        # Score = (likes * LIKE_WEIGHT) + (comments * COMMENT_WEIGHT) / age_hours
        trending_posts = (
            session.query(Post)
            .join(User, Post.user_id == User.id)
            .filter(
                Post.created_at >= cutoff,
                Post.deleted_at.is_(None),  # Not soft-deleted
            )
            .order_by(
                # Order by engagement score (simplified)
                desc(
                    (Post.likes_count * TRENDING_LIKE_WEIGHT) +
                    (Post.comments_count * TRENDING_COMMENT_WEIGHT)
                ),
                desc(Post.created_at),  # Recency as tiebreaker
            )
            .limit(200)  # Cache top 200 posts
            .all()
        )
        
        logger.info(f"Found {len(trending_posts)} trending posts")
        
        # Serialize for cache
        serialized_posts = [
            _serialize_post_for_cache(post)
            for post in trending_posts
        ]
        
        # Cache in Redis with pagination support
        # Store as a sorted set for efficient pagination
        pipe = redis.pipeline()
        
        # Clear old cache
        explore_pattern = redis_keys.explore_feed_pattern()
        for key in redis.scan_iter(match=explore_pattern):
            pipe.delete(key)
        
        # Store the full feed
        cache_key = redis_keys.cache("explore_feed", "full")
        pipe.set(cache_key, json.dumps(serialized_posts), ex=TRENDING_FEED_TTL)
        
        # Also cache individual pages for common page sizes
        for per_page in [10, 20, 50]:
            for page in range(1, 6):  # Cache first 5 pages
                start = (page - 1) * per_page
                end = start + per_page
                page_posts = serialized_posts[start:end]
                
                if page_posts:
                    page_key = redis_keys.explore_feed(page, per_page)
                    pipe.set(page_key, json.dumps({
                        "items": page_posts,
                        "total": len(serialized_posts),
                        "page": page,
                        "per_page": per_page,
                    }), ex=TRENDING_FEED_TTL)
        
        pipe.execute()
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"Trending feed generated in {duration:.2f}s, {len(trending_posts)} posts cached")
        
        return {
            "status": "success",
            "posts_count": len(trending_posts),
            "duration_seconds": duration,
            "cached_pages": 5,
        }
        
    except Exception as exc:
        logger.error(f"Failed to generate trending feed: {exc}")
        raise
    finally:
        session.close()


# =============================================================================
# User Feed Cache Invalidation
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.feed_tasks.invalidate_user_feed_cache",
    bind=True,
)
def invalidate_user_feed_cache(self, user_id: int) -> dict[str, Any]:
    """
    Invalidate a user's home feed cache.
    
    Called when:
    - User follows/unfollows someone
    - A followed user posts something new
    - User's feed preferences change
    
    Args:
        user_id: ID of the user whose cache to invalidate
        
    Returns:
        Dict with invalidation stats
    """
    logger.debug(f"Invalidating feed cache for user {user_id}")
    
    try:
        redis = _get_redis_client()
        
        # Get pattern for all cached pages for this user
        pattern = redis_keys.home_feed_pattern(user_id)
        
        # Delete all matching keys
        deleted_count = 0
        for key in redis.scan_iter(match=pattern):
            redis.delete(key)
            deleted_count += 1
        
        logger.debug(f"Invalidated {deleted_count} cache entries for user {user_id}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "keys_deleted": deleted_count,
        }
        
    except Exception as exc:
        logger.error(f"Failed to invalidate feed cache: {exc}")
        # Don't retry - cache invalidation is best-effort
        return {
            "status": "error",
            "user_id": user_id,
            "error": str(exc),
        }


# =============================================================================
# Post Fanout to Followers
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.feed_tasks.fanout_post_to_followers",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def fanout_post_to_followers(
    self,
    post_id: int,
    author_id: int,
) -> dict[str, Any]:
    """
    Fan out a new post to all followers' feeds.
    
    This implements the "push" model for feed distribution:
    - When a user posts, we immediately push it to all followers' cached feeds
    - Ensures fast feed reads at the cost of slower writes
    
    For users with many followers (celebrities), consider:
    - Hybrid approach: push to active followers, pull for inactive
    - Rate limiting the fanout
    - Chunking into smaller batches
    
    Args:
        post_id: ID of the new post
        author_id: ID of the post author
        
    Returns:
        Dict with fanout stats
    """
    from app.models import followers
    from app.models.post import Post
    from sqlalchemy import select
    
    logger.info(f"Starting fanout for post {post_id} from user {author_id}")
    start_time = datetime.now(timezone.utc)
    
    session = _get_sync_db_session()
    redis = _get_redis_client()
    
    try:
        # Get the post data
        post = session.query(Post).get(post_id)
        if not post:
            return {"status": "error", "reason": "post_not_found"}
        
        # Serialize post for cache
        serialized_post = _serialize_post_for_cache(post)
        post_json = json.dumps(serialized_post)
        
        # Get all follower IDs
        result = session.execute(
            select(followers.c.follower_id).where(followers.c.followed_id == author_id)
        )
        follower_ids = [row[0] for row in result]
        
        if not follower_ids:
            return {"status": "success", "followers_updated": 0}
        
        logger.info(f"Fanning out to {len(follower_ids)} followers")
        
        # For each follower, update their cached feed
        updated_count = 0
        errors_count = 0
        
        # Use pipeline for efficiency
        pipe = redis.pipeline()
        
        for follower_id in follower_ids:
            try:
                # Get the user's cached feed
                # We need to prepend the new post to their feed
                for per_page in [20]:  # Most common page size
                    cache_key = redis_keys.home_feed(follower_id, 1, per_page)
                    cached = redis.get(cache_key)
                    
                    if cached:
                        # Parse existing cache
                        feed_data = json.loads(cached)
                        items = feed_data.get("items", [])
                        
                        # Prepend new post
                        items.insert(0, serialized_post)
                        
                        # Trim to page size
                        items = items[:per_page]
                        
                        # Update cache
                        feed_data["items"] = items
                        feed_data["total"] = feed_data.get("total", 0) + 1
                        
                        pipe.set(cache_key, json.dumps(feed_data), ex=HOME_FEED_TTL)
                        updated_count += 1
                    else:
                        # No cache exists, invalidate so next read fetches fresh
                        invalidate_user_feed_cache.delay(follower_id)
                        
            except Exception as e:
                logger.warning(f"Failed to update feed for follower {follower_id}: {e}")
                errors_count += 1
        
        pipe.execute()
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"Fanout complete: {updated_count} feeds updated, "
            f"{errors_count} errors, {duration:.2f}s"
        )
        
        return {
            "status": "success",
            "post_id": post_id,
            "followers_count": len(follower_ids),
            "feeds_updated": updated_count,
            "errors": errors_count,
            "duration_seconds": duration,
        }
        
    except Exception as exc:
        logger.error(f"Fanout failed for post {post_id}: {exc}")
        raise self.retry(exc=exc)
    finally:
        session.close()


# =============================================================================
# Precompute User Feeds (Optional - for power users)
# =============================================================================

@celery_app.task(
    name="app.workers.tasks.feed_tasks.precompute_user_feed",
    bind=True,
)
def precompute_user_feed(self, user_id: int) -> dict[str, Any]:
    """
    Precompute and cache a user's home feed.
    
    Useful for:
    - Users returning after being away
    - Preparing feeds before peak hours
    - Background refresh for VIP users
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dict with computation stats
    """
    from app.models import followers
    from app.models.post import Post
    from app.models.user import User
    from sqlalchemy import select, desc
    
    logger.info(f"Precomputing feed for user {user_id}")
    
    session = _get_sync_db_session()
    redis = _get_redis_client()
    
    try:
        # Get user's following list
        result = session.execute(
            select(followers.c.followed_id).where(followers.c.follower_id == user_id)
        )
        following_ids = [row[0] for row in result]
        
        # Include user's own posts
        following_ids.append(user_id)
        
        if not following_ids:
            return {"status": "success", "posts_cached": 0}
        
        # Query posts from followed users
        posts = (
            session.query(Post)
            .join(User, Post.user_id == User.id)
            .filter(
                Post.user_id.in_(following_ids),
                Post.deleted_at.is_(None),
            )
            .order_by(desc(Post.created_at))
            .limit(100)  # Cache first 100 posts
            .all()
        )
        
        # Serialize
        serialized_posts = [
            _serialize_post_for_cache(post)
            for post in posts
        ]
        
        # Cache paginated
        pipe = redis.pipeline()
        
        for per_page in [10, 20]:
            for page in range(1, 6):
                start = (page - 1) * per_page
                end = start + per_page
                page_posts = serialized_posts[start:end]
                
                if page_posts:
                    cache_key = redis_keys.home_feed(user_id, page, per_page)
                    pipe.set(cache_key, json.dumps({
                        "items": page_posts,
                        "total": len(serialized_posts),
                        "page": page,
                        "per_page": per_page,
                    }), ex=HOME_FEED_TTL)
        
        pipe.execute()
        
        logger.info(f"Precomputed feed for user {user_id}: {len(posts)} posts")
        
        return {
            "status": "success",
            "user_id": user_id,
            "posts_cached": len(posts),
        }
        
    except Exception as exc:
        logger.error(f"Failed to precompute feed for user {user_id}: {exc}")
        raise
    finally:
        session.close()

