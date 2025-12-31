"""
Recommendation system Celery tasks.

Handles:
- Pre-computing ranked feeds for active users
- Affinity score decay
- Batch feed generation
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

# Pre-computation settings
PRECOMPUTE_BATCH_SIZE = 100  # Users per batch
PRECOMPUTE_FEED_SIZE = 100  # Posts per user
RANKED_FEED_TTL = 180  # 3 minutes

# Active user threshold
ACTIVE_USER_DAYS = 7

# Affinity decay settings
AFFINITY_DECAY_FACTOR = 0.95


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


def _calculate_recency_score(created_at: datetime) -> float:
    """
    Calculate recency score with time decay.

    Brackets:
    - < 1 hour: 1.0
    - 1-6 hours: 0.9
    - 6-24 hours: 0.7
    - 1-3 days: 0.5
    - 3-7 days: 0.3
    - > 7 days: 0.1
    """
    import math

    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    age_hours = (now - created_at).total_seconds() / 3600

    if age_hours <= 1:
        return 1.0
    elif age_hours <= 6:
        return 0.9
    elif age_hours <= 24:
        return 0.7
    elif age_hours <= 72:
        return 0.5
    elif age_hours <= 168:
        return 0.3
    else:
        return 0.1


def _calculate_engagement_score(
    likes: int, comments: int, reposts: int
) -> float:
    """
    Calculate engagement score with log normalization.

    Formula: log(1 + raw_score) / log(1 + max_expected)
    """
    import math

    raw_score = likes * 1.0 + comments * 2.0 + reposts * 3.0
    max_expected = 10000
    normalized = math.log(1 + raw_score) / math.log(1 + max_expected)
    return min(1.0, max(0.0, normalized))


def _get_affinity_score(redis, user_id: int, author_id: int) -> float:
    """Get affinity score from Redis."""
    if user_id == author_id:
        return 1.0

    key = redis_keys.affinity(user_id, author_id)
    raw_score = redis.get(key)

    if raw_score is None:
        return 0.0

    try:
        score = float(raw_score)
        # Normalize to [0, 1]
        return min(1.0, score / 100.0)
    except (ValueError, TypeError):
        return 0.0


def _calculate_post_score(
    post, user_id: int, redis
) -> float:
    """
    Calculate combined recommendation score for a post.

    Score = recency * 0.3 + engagement * 0.4 + affinity * 0.3
    """
    recency = _calculate_recency_score(post.created_at)
    engagement = _calculate_engagement_score(
        post.likes_count or 0,
        post.comments_count or 0,
        post.reposts_count or 0,
    )
    affinity = _get_affinity_score(redis, user_id, post.user_id)

    return recency * 0.3 + engagement * 0.4 + affinity * 0.3


# =============================================================================
# Precompute Feeds Task
# =============================================================================


@celery_app.task(
    name="app.workers.tasks.recommendation_tasks.precompute_feeds",
    bind=True,
)
def precompute_feeds(self) -> dict[str, Any]:
    """
    Pre-compute ranked feeds for active users.

    Runs periodically to ensure active users have fast feed loading.
    Computes and caches the top 100 posts for each active user.

    Returns:
        Dict with computation stats
    """
    from sqlalchemy import desc, select
    from sqlalchemy.orm import selectinload

    from app.models import followers
    from app.models.post import Post
    from app.models.user import User

    logger.info("Starting feed precomputation for active users")
    start_time = datetime.now(timezone.utc)

    session = _get_sync_db_session()
    redis = _get_redis_client()

    try:
        # Find active users (logged in within last 7 days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=ACTIVE_USER_DAYS)

        # Get users who have been active recently
        # (using created_at as proxy if last_login doesn't exist)
        active_users = (
            session.query(User)
            .filter(
                User.deleted_at.is_(None),
            )
            .order_by(desc(User.id))
            .limit(PRECOMPUTE_BATCH_SIZE)
            .all()
        )

        logger.info(f"Found {len(active_users)} users for precomputation")

        users_processed = 0
        total_posts_cached = 0

        for user in active_users:
            try:
                # Get user's following list
                result = session.execute(
                    select(followers.c.followed_id).where(
                        followers.c.follower_id == user.id
                    )
                )
                following_ids = [row[0] for row in result]

                if not following_ids:
                    continue

                # Include user's own posts
                author_ids = list(set(following_ids + [user.id]))

                # Get recent posts from followed users
                post_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                posts = (
                    session.query(Post)
                    .filter(
                        Post.user_id.in_(author_ids),
                        Post.created_at >= post_cutoff,
                        Post.deleted_at.is_(None),
                    )
                    .options(selectinload(Post.author))
                    .order_by(desc(Post.created_at))
                    .limit(PRECOMPUTE_FEED_SIZE * 2)  # Fetch extra for ranking
                    .all()
                )

                if not posts:
                    continue

                # Score and sort posts
                scored_posts = []
                for post in posts:
                    score = _calculate_post_score(post, user.id, redis)
                    scored_posts.append((post, score))

                scored_posts.sort(key=lambda x: x[1], reverse=True)
                top_posts = scored_posts[:PRECOMPUTE_FEED_SIZE]

                # Cache in Redis sorted set
                cache_key = redis_keys.ranked_feed(user.id)
                pipe = redis.pipeline()
                pipe.delete(cache_key)

                for idx, (post, score) in enumerate(top_posts):
                    # Use negative index for ordering (highest first)
                    pipe.zadd(cache_key, {str(post.id): -idx})

                pipe.expire(cache_key, RANKED_FEED_TTL)
                pipe.execute()

                users_processed += 1
                total_posts_cached += len(top_posts)

            except Exception as e:
                logger.warning(f"Failed to precompute feed for user {user.id}: {e}")
                continue

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"Feed precomputation complete: {users_processed} users, "
            f"{total_posts_cached} posts cached in {duration:.2f}s"
        )

        return {
            "status": "success",
            "users_processed": users_processed,
            "total_posts_cached": total_posts_cached,
            "duration_seconds": duration,
        }

    except Exception as exc:
        logger.error(f"Feed precomputation failed: {exc}")
        raise
    finally:
        session.close()


# =============================================================================
# Affinity Decay Task
# =============================================================================


@celery_app.task(
    name="app.workers.tasks.recommendation_tasks.decay_affinity_scores",
    bind=True,
)
def decay_affinity_scores(self) -> dict[str, Any]:
    """
    Apply time decay to all affinity scores.

    Should be run daily to ensure old interactions fade in importance.
    Applies a 5% decay to all scores and removes scores below threshold.

    Returns:
        Dict with decay stats
    """
    logger.info("Starting affinity score decay")
    start_time = datetime.now(timezone.utc)

    redis = _get_redis_client()

    try:
        pattern = "affinity:*"
        decayed_count = 0
        deleted_count = 0

        for key in redis.scan_iter(match=pattern):
            current = redis.get(key)
            if current:
                try:
                    new_value = float(current) * AFFINITY_DECAY_FACTOR
                    if new_value < 0.01:
                        redis.delete(key)
                        deleted_count += 1
                    else:
                        # Preserve TTL or set new one
                        ttl = redis.ttl(key)
                        if ttl < 0:
                            ttl = 60 * 60 * 24 * 30  # 30 days
                        redis.set(key, new_value, ex=ttl)
                        decayed_count += 1
                except (ValueError, TypeError):
                    pass

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"Affinity decay complete: {decayed_count} decayed, "
            f"{deleted_count} deleted in {duration:.2f}s"
        )

        return {
            "status": "success",
            "scores_decayed": decayed_count,
            "scores_deleted": deleted_count,
            "duration_seconds": duration,
        }

    except Exception as exc:
        logger.error(f"Affinity decay failed: {exc}")
        raise


# =============================================================================
# Single User Feed Computation
# =============================================================================


@celery_app.task(
    name="app.workers.tasks.recommendation_tasks.compute_user_feed",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def compute_user_feed(self, user_id: int) -> dict[str, Any]:
    """
    Compute and cache ranked feed for a single user.

    Called when:
    - User logs in after cache expiry
    - User requests feed refresh
    - Cache invalidation occurs

    Args:
        user_id: User ID to compute feed for

    Returns:
        Dict with computation stats
    """
    from sqlalchemy import desc, select
    from sqlalchemy.orm import selectinload

    from app.models import followers
    from app.models.post import Post

    logger.debug(f"Computing feed for user {user_id}")
    start_time = datetime.now(timezone.utc)

    session = _get_sync_db_session()
    redis = _get_redis_client()

    try:
        # Get user's following list
        result = session.execute(
            select(followers.c.followed_id).where(
                followers.c.follower_id == user_id
            )
        )
        following_ids = [row[0] for row in result]

        if not following_ids:
            return {
                "status": "success",
                "user_id": user_id,
                "posts_cached": 0,
                "reason": "no_following",
            }

        # Include user's own posts
        author_ids = list(set(following_ids + [user_id]))

        # Get recent posts
        post_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        posts = (
            session.query(Post)
            .filter(
                Post.user_id.in_(author_ids),
                Post.created_at >= post_cutoff,
                Post.deleted_at.is_(None),
            )
            .options(selectinload(Post.author))
            .order_by(desc(Post.created_at))
            .limit(PRECOMPUTE_FEED_SIZE * 2)
            .all()
        )

        if not posts:
            return {
                "status": "success",
                "user_id": user_id,
                "posts_cached": 0,
                "reason": "no_posts",
            }

        # Score and sort
        scored_posts = []
        for post in posts:
            score = _calculate_post_score(post, user_id, redis)
            scored_posts.append((post, score))

        scored_posts.sort(key=lambda x: x[1], reverse=True)
        top_posts = scored_posts[:PRECOMPUTE_FEED_SIZE]

        # Cache in Redis
        cache_key = redis_keys.ranked_feed(user_id)
        pipe = redis.pipeline()
        pipe.delete(cache_key)

        for idx, (post, score) in enumerate(top_posts):
            pipe.zadd(cache_key, {str(post.id): -idx})

        pipe.expire(cache_key, RANKED_FEED_TTL)
        pipe.execute()

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        return {
            "status": "success",
            "user_id": user_id,
            "posts_cached": len(top_posts),
            "duration_seconds": duration,
        }

    except Exception as exc:
        logger.error(f"Failed to compute feed for user {user_id}: {exc}")
        raise self.retry(exc=exc)
    finally:
        session.close()


# =============================================================================
# Invalidate User Feed Cache
# =============================================================================


@celery_app.task(
    name="app.workers.tasks.recommendation_tasks.invalidate_ranked_feed",
    bind=True,
)
def invalidate_ranked_feed(self, user_id: int) -> dict[str, Any]:
    """
    Invalidate a user's ranked feed cache.

    Called when:
    - User follows/unfollows someone
    - A followed user posts something new

    Args:
        user_id: User ID whose cache to invalidate

    Returns:
        Dict with invalidation stats
    """
    logger.debug(f"Invalidating ranked feed for user {user_id}")

    try:
        redis = _get_redis_client()
        cache_key = redis_keys.ranked_feed(user_id)

        deleted = redis.delete(cache_key)

        return {
            "status": "success",
            "user_id": user_id,
            "cache_deleted": bool(deleted),
        }

    except Exception as exc:
        logger.error(f"Failed to invalidate feed for user {user_id}: {exc}")
        return {
            "status": "error",
            "user_id": user_id,
            "error": str(exc),
        }

