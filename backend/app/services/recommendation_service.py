"""
Recommendation service for personalized feed ranking.

Implements a rule-based scoring system for feed personalization:
- Recency score: Time decay over 7 days
- Engagement score: Weighted likes, comments, reposts with log normalization
- Author affinity: User interaction history with time decay

Can be run as:
- On-demand for real-time feed requests
- Background job for pre-computation of popular user feeds
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Sequence

from redis.asyncio import Redis
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis_keys import redis_keys
from app.models import followers
from app.models.post import Post

if TYPE_CHECKING:
    from app.repositories.post_repository import PostRepository

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Score weights (must sum to 1.0)
WEIGHT_RECENCY = 0.3
WEIGHT_ENGAGEMENT = 0.4
WEIGHT_AFFINITY = 0.3

# Engagement weights
LIKE_WEIGHT = 1.0
COMMENT_WEIGHT = 2.0
REPOST_WEIGHT = 3.0

# Affinity configuration
AFFINITY_LIKE_SCORE = 1.0
AFFINITY_COMMENT_SCORE = 3.0
AFFINITY_PROFILE_VISIT_SCORE = 0.5
AFFINITY_DECAY_DAYS = 30  # Affinity decays over 30 days
AFFINITY_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days

# Feed configuration
DEFAULT_FEED_LIMIT = 50
MAX_FEED_LIMIT = 200
RANKED_FEED_TTL_SECONDS = 180  # 3 minutes
ACTIVE_USER_THRESHOLD_DAYS = 7  # Users active in last 7 days


# =============================================================================
# Data Classes
# =============================================================================


@dataclass(frozen=True)
class RecencyBracket:
    """Defines a time bracket for recency scoring."""

    max_hours: float
    score: float


# Recency brackets from requirements
RECENCY_BRACKETS: tuple[RecencyBracket, ...] = (
    RecencyBracket(max_hours=1, score=1.0),
    RecencyBracket(max_hours=6, score=0.9),
    RecencyBracket(max_hours=24, score=0.7),
    RecencyBracket(max_hours=72, score=0.5),  # 3 days
    RecencyBracket(max_hours=168, score=0.3),  # 7 days
)
DEFAULT_RECENCY_SCORE = 0.1  # Posts older than 7 days


@dataclass
class ScoredPost:
    """A post with its computed recommendation score."""

    post: Post
    score: float
    recency_score: float
    engagement_score: float
    affinity_score: float


# =============================================================================
# Recommendation Service
# =============================================================================


class RecommendationService:
    """
    Service for computing personalized feed recommendations.

    Uses a rule-based scoring algorithm combining:
    - Recency: How fresh is the post
    - Engagement: How popular is the post
    - Affinity: How often does the user interact with the author

    Example usage:
        service = RecommendationService(db, redis)
        feed = await service.get_ranked_feed(user_id, following_ids, limit=50)
    """

    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        """
        Initialize recommendation service.

        Args:
            db: Async database session
            redis: Async Redis client
        """
        self.db = db
        self.redis = redis

    # =========================================================================
    # Public API
    # =========================================================================

    async def get_ranked_feed(
        self,
        user_id: int,
        following_ids: list[int],
        *,
        limit: int = DEFAULT_FEED_LIMIT,
        max_age_days: int = 7,
    ) -> list[Post]:
        """
        Get personalized ranked feed for a user.

        Fetches recent posts from followed users, scores them,
        and returns the top N sorted by score.

        Args:
            user_id: Current user's ID
            following_ids: List of user IDs the user follows
            limit: Maximum number of posts to return
            max_age_days: Maximum age of posts to consider

        Returns:
            List of Post objects sorted by recommendation score (highest first)
        """
        limit = min(limit, MAX_FEED_LIMIT)

        if not following_ids:
            logger.debug(f"User {user_id} follows no one, returning empty feed")
            return []

        # Include user's own posts
        author_ids = list(set(following_ids + [user_id]))

        # Fetch recent posts from followed users
        posts = await self._fetch_candidate_posts(
            author_ids=author_ids,
            max_age_days=max_age_days,
            fetch_limit=limit * 3,  # Fetch more than needed for better ranking
        )

        if not posts:
            return []

        # Score all posts
        scored_posts = await self._score_posts(posts, user_id)

        # Sort by score descending
        scored_posts.sort(key=lambda sp: sp.score, reverse=True)

        # Return top N posts
        return [sp.post for sp in scored_posts[:limit]]

    def calculate_post_score(
        self,
        post: Post,
        user_id: int,
        affinity_score: float,
    ) -> ScoredPost:
        """
        Calculate the recommendation score for a single post.

        Score = (recency * 0.3) + (engagement * 0.4) + (affinity * 0.3)

        Args:
            post: The post to score
            user_id: Current user's ID (for context)
            affinity_score: Pre-computed affinity score for the author

        Returns:
            ScoredPost with individual and combined scores
        """
        recency = self.recency_score(post.created_at)
        engagement = self.engagement_score(post)

        combined_score = (
            recency * WEIGHT_RECENCY
            + engagement * WEIGHT_ENGAGEMENT
            + affinity_score * WEIGHT_AFFINITY
        )

        return ScoredPost(
            post=post,
            score=combined_score,
            recency_score=recency,
            engagement_score=engagement,
            affinity_score=affinity_score,
        )

    # =========================================================================
    # Scoring Components
    # =========================================================================

    def recency_score(self, timestamp: datetime | None) -> float:
        """
        Calculate recency score with time decay.

        Uses bracket-based scoring:
        - < 1 hour: 1.0
        - 1-6 hours: 0.9
        - 6-24 hours: 0.7
        - 1-3 days: 0.5
        - 3-7 days: 0.3
        - > 7 days: 0.1

        Args:
            timestamp: Post creation timestamp

        Returns:
            Score between 0.1 and 1.0
        """
        if timestamp is None:
            return DEFAULT_RECENCY_SCORE

        # Ensure timezone-aware comparison
        now = datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        age = now - timestamp
        age_hours = age.total_seconds() / 3600

        for bracket in RECENCY_BRACKETS:
            if age_hours <= bracket.max_hours:
                return bracket.score

        return DEFAULT_RECENCY_SCORE

    def engagement_score(self, post: Post) -> float:
        """
        Calculate engagement score with log normalization.

        Formula:
        raw_score = (likes * 1) + (comments * 2) + (reposts * 3)
        normalized = log(1 + raw_score) / log(1 + max_expected)

        Log normalization prevents viral posts from completely
        dominating the feed while still giving them an advantage.

        Args:
            post: The post to score

        Returns:
            Score between 0.0 and 1.0
        """
        # Handle None and negative values
        likes = max(0, post.likes_count or 0)
        comments = max(0, post.comments_count or 0)
        reposts = max(0, post.reposts_count or 0)

        raw_score = (
            likes * LIKE_WEIGHT + comments * COMMENT_WEIGHT + reposts * REPOST_WEIGHT
        )

        # Log normalization
        # Using log(1 + x) to handle zero gracefully
        # Max expected is ~10000 interactions for normalization
        max_expected = 10000
        normalized = math.log(1 + raw_score) / math.log(1 + max_expected)

        # Clamp to [0, 1]
        return min(1.0, max(0.0, normalized))

    async def author_affinity(self, user_id: int, author_id: int) -> float:
        """
        Get affinity score between a user and an author.

        Affinity is based on interaction history:
        - Liking author's posts: +1.0 per like
        - Commenting on author's posts: +3.0 per comment
        - Visiting author's profile: +0.5 per visit

        Score decays over time (30 day half-life).

        Args:
            user_id: Current user's ID
            author_id: Post author's ID

        Returns:
            Affinity score between 0.0 and 1.0
        """
        if user_id == author_id:
            # Users have maximum affinity with themselves
            return 1.0

        key = redis_keys.affinity(user_id, author_id)
        raw_score = await self.redis.get(key)

        if raw_score is None:
            return 0.0

        try:
            score = float(raw_score)
        except (ValueError, TypeError):
            return 0.0

        # Normalize to [0, 1] range
        # Assuming max practical affinity score of ~100
        max_affinity = 100.0
        normalized = min(1.0, score / max_affinity)

        return normalized

    # =========================================================================
    # Affinity Tracking
    # =========================================================================

    async def record_like_interaction(self, user_id: int, author_id: int) -> None:
        """
        Record a like interaction for affinity tracking.

        Args:
            user_id: User who liked
            author_id: Author of the liked post
        """
        await self._update_affinity(user_id, author_id, AFFINITY_LIKE_SCORE)

    async def record_comment_interaction(self, user_id: int, author_id: int) -> None:
        """
        Record a comment interaction for affinity tracking.

        Args:
            user_id: User who commented
            author_id: Author of the post
        """
        await self._update_affinity(user_id, author_id, AFFINITY_COMMENT_SCORE)

    async def record_profile_visit(self, user_id: int, visited_user_id: int) -> None:
        """
        Record a profile visit for affinity tracking.

        Args:
            user_id: User who visited
            visited_user_id: User whose profile was visited
        """
        await self._update_affinity(user_id, visited_user_id, AFFINITY_PROFILE_VISIT_SCORE)

    async def _update_affinity(
        self, user_id: int, author_id: int, increment: float
    ) -> None:
        """
        Update affinity score in Redis.

        Uses INCRBYFLOAT for atomic increment and refreshes TTL.

        Args:
            user_id: Current user's ID
            author_id: Author's ID
            increment: Score to add
        """
        if user_id == author_id:
            return  # Don't track self-affinity

        key = redis_keys.affinity(user_id, author_id)

        # Atomic increment
        await self.redis.incrbyfloat(key, increment)

        # Refresh TTL
        await self.redis.expire(key, AFFINITY_TTL_SECONDS)

        logger.debug(
            f"Updated affinity {user_id}->{author_id}: +{increment}"
        )

    async def decay_affinity_scores(self, user_id: int) -> int:
        """
        Apply time decay to all affinity scores for a user.

        This should be called periodically (e.g., daily) to
        ensure old interactions fade in importance.

        Args:
            user_id: User whose affinity scores to decay

        Returns:
            Number of scores decayed
        """
        pattern = f"affinity:{user_id}:*"
        decay_factor = 0.95  # 5% decay per application

        decayed_count = 0
        async for key in self.redis.scan_iter(match=pattern):
            current = await self.redis.get(key)
            if current:
                try:
                    new_value = float(current) * decay_factor
                    if new_value < 0.01:
                        await self.redis.delete(key)
                    else:
                        await self.redis.set(key, new_value, ex=AFFINITY_TTL_SECONDS)
                    decayed_count += 1
                except (ValueError, TypeError):
                    pass

        return decayed_count

    # =========================================================================
    # Ranked Feed Caching
    # =========================================================================

    async def cache_ranked_feed(
        self,
        user_id: int,
        posts: list[Post],
        ttl: int = RANKED_FEED_TTL_SECONDS,
    ) -> None:
        """
        Cache a pre-computed ranked feed for a user.

        Stores post IDs in a Redis sorted set with scores.

        Args:
            user_id: User's ID
            posts: Ordered list of posts (highest score first)
            ttl: Cache TTL in seconds
        """
        key = redis_keys.ranked_feed(user_id)

        if not posts:
            return

        # Store as sorted set with position as score (for ordering)
        pipe = self.redis.pipeline()
        pipe.delete(key)

        for idx, post in enumerate(posts):
            # Use negative index so highest ranked comes first
            pipe.zadd(key, {str(post.id): -idx})

        pipe.expire(key, ttl)
        await pipe.execute()

        logger.debug(f"Cached {len(posts)} posts for user {user_id}")

    async def get_cached_ranked_feed(
        self, user_id: int, limit: int = DEFAULT_FEED_LIMIT
    ) -> list[int] | None:
        """
        Get cached ranked feed post IDs.

        Args:
            user_id: User's ID
            limit: Maximum posts to return

        Returns:
            List of post IDs in ranked order, or None if cache miss
        """
        key = redis_keys.ranked_feed(user_id)

        # Get from sorted set (ordered by score ascending = original order)
        post_ids = await self.redis.zrange(key, 0, limit - 1)

        if not post_ids:
            return None

        return [int(pid) for pid in post_ids]

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _fetch_candidate_posts(
        self,
        author_ids: list[int],
        max_age_days: int,
        fetch_limit: int,
    ) -> Sequence[Post]:
        """
        Fetch candidate posts for ranking.

        Args:
            author_ids: List of author IDs to include
            max_age_days: Maximum post age in days
            fetch_limit: Maximum posts to fetch

        Returns:
            Sequence of Post objects with authors loaded
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        result = await self.db.execute(
            select(Post)
            .where(
                Post.user_id.in_(author_ids),
                Post.created_at >= cutoff,
                Post.deleted_at.is_(None),
            )
            .options(selectinload(Post.author))
            .order_by(desc(Post.created_at))
            .limit(fetch_limit)
        )

        return result.scalars().all()

    async def _score_posts(
        self, posts: Sequence[Post], user_id: int
    ) -> list[ScoredPost]:
        """
        Score a batch of posts for a user.

        Pre-fetches all affinity scores for efficiency.

        Args:
            posts: Posts to score
            user_id: Current user's ID

        Returns:
            List of ScoredPost objects
        """
        # Collect unique author IDs
        author_ids = list({post.user_id for post in posts})

        # Batch fetch affinity scores
        affinities: dict[int, float] = {}
        for author_id in author_ids:
            affinities[author_id] = await self.author_affinity(user_id, author_id)

        # Score each post
        scored_posts = []
        for post in posts:
            affinity = affinities.get(post.user_id, 0.0)
            scored = self.calculate_post_score(post, user_id, affinity)
            scored_posts.append(scored)

        return scored_posts


# =============================================================================
# Factory Function
# =============================================================================


def get_recommendation_service(
    db: AsyncSession, redis: Redis
) -> RecommendationService:
    """
    Factory function to create a RecommendationService.

    Args:
        db: Async database session
        redis: Async Redis client

    Returns:
        Configured RecommendationService instance
    """
    return RecommendationService(db, redis)

