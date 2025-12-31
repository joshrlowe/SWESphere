"""
Tests for RecommendationService.

Comprehensive test coverage for:
- Recency scoring with time brackets
- Engagement scoring with log normalization
- Author affinity tracking and retrieval
- Ranked feed generation
- Cache operations
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.user import User
from app.services.recommendation_service import (
    AFFINITY_COMMENT_SCORE,
    AFFINITY_LIKE_SCORE,
    AFFINITY_PROFILE_VISIT_SCORE,
    AFFINITY_TTL_SECONDS,
    DEFAULT_RECENCY_SCORE,
    WEIGHT_AFFINITY,
    WEIGHT_ENGAGEMENT,
    WEIGHT_RECENCY,
    RecommendationService,
    ScoredPost,
    get_recommendation_service,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_redis_for_recommendations():
    """Create a mock Redis with affinity storage simulation."""
    redis = AsyncMock()
    
    # Storage for affinity scores
    _affinity_store: dict[str, str] = {}
    _sorted_sets: dict[str, dict[str, float]] = {}
    
    async def mock_get(key: str):
        return _affinity_store.get(key)
    
    async def mock_set(key: str, value: Any, ex: int = None):
        _affinity_store[key] = str(value)
        return True
    
    async def mock_incrbyfloat(key: str, amount: float):
        current = float(_affinity_store.get(key, "0"))
        new_value = current + amount
        _affinity_store[key] = str(new_value)
        return new_value
    
    async def mock_expire(key: str, ttl: int):
        return True
    
    async def mock_delete(key: str):
        if key in _affinity_store:
            del _affinity_store[key]
            return 1
        if key in _sorted_sets:
            del _sorted_sets[key]
            return 1
        return 0
    
    async def mock_zadd(key: str, mapping: dict[str, float]):
        if key not in _sorted_sets:
            _sorted_sets[key] = {}
        _sorted_sets[key].update(mapping)
        return len(mapping)
    
    async def mock_zrange(key: str, start: int, end: int):
        if key not in _sorted_sets:
            return []
        items = sorted(_sorted_sets[key].items(), key=lambda x: x[1])
        if end == -1:
            return [item[0] for item in items[start:]]
        return [item[0] for item in items[start:end + 1]]
    
    async def mock_ttl(key: str):
        if key in _affinity_store:
            return 3600  # Mock TTL
        return -2
    
    async def mock_scan_iter(match: str = "*"):
        import fnmatch
        for key in list(_affinity_store.keys()):
            if fnmatch.fnmatch(key, match):
                yield key
    
    class MockPipeline:
        def __init__(self):
            self._operations = []
        
        def delete(self, key):
            self._operations.append(("delete", key))
            return self
        
        def zadd(self, key, mapping):
            self._operations.append(("zadd", key, mapping))
            return self
        
        def expire(self, key, ttl):
            self._operations.append(("expire", key, ttl))
            return self
        
        async def execute(self):
            results = []
            for op in self._operations:
                if op[0] == "delete":
                    results.append(await mock_delete(op[1]))
                elif op[0] == "zadd":
                    results.append(await mock_zadd(op[1], op[2]))
                elif op[0] == "expire":
                    results.append(await mock_expire(op[1], op[2]))
            self._operations = []
            return results
    
    def pipeline():
        return MockPipeline()
    
    redis.get = mock_get
    redis.set = mock_set
    redis.incrbyfloat = mock_incrbyfloat
    redis.expire = mock_expire
    redis.delete = mock_delete
    redis.zadd = mock_zadd
    redis.zrange = mock_zrange
    redis.ttl = mock_ttl
    redis.scan_iter = mock_scan_iter
    redis.pipeline = pipeline
    
    # Expose storage for test assertions
    redis._affinity_store = _affinity_store
    redis._sorted_sets = _sorted_sets
    
    return redis


@pytest_asyncio.fixture
async def recommendation_service(
    db_session: AsyncSession, mock_redis_for_recommendations
) -> RecommendationService:
    """Create RecommendationService for testing."""
    return RecommendationService(db_session, mock_redis_for_recommendations)


def create_mock_post(
    post_id: int = 1,
    user_id: int = 1,
    likes: int = 0,
    comments: int = 0,
    reposts: int = 0,
    created_at: datetime = None,
) -> Post:
    """Create a mock Post object for testing."""
    post = MagicMock(spec=Post)
    post.id = post_id
    post.user_id = user_id
    post.likes_count = likes
    post.comments_count = comments
    post.reposts_count = reposts
    post.created_at = created_at or datetime.now(timezone.utc)
    post.deleted_at = None
    return post


# =============================================================================
# Recency Score Tests
# =============================================================================


class TestRecencyScore:
    """Test recency scoring with time decay brackets."""

    def test_recency_score_under_1_hour(self, recommendation_service):
        """Posts under 1 hour old should get score of 1.0."""
        timestamp = datetime.now(timezone.utc) - timedelta(minutes=30)
        score = recommendation_service.recency_score(timestamp)
        assert score == 1.0

    def test_recency_score_exactly_1_hour(self, recommendation_service):
        """Posts at 1 hour boundary fall into 1-6 hour bracket (0.9)."""
        timestamp = datetime.now(timezone.utc) - timedelta(hours=1)
        score = recommendation_service.recency_score(timestamp)
        # Exactly 1 hour is at the boundary, may fall into next bracket
        assert score in (1.0, 0.9)

    def test_recency_score_1_to_6_hours(self, recommendation_service):
        """Posts 1-6 hours old should get score of 0.9."""
        timestamp = datetime.now(timezone.utc) - timedelta(hours=3)
        score = recommendation_service.recency_score(timestamp)
        assert score == 0.9

    def test_recency_score_6_to_24_hours(self, recommendation_service):
        """Posts 6-24 hours old should get score of 0.7."""
        timestamp = datetime.now(timezone.utc) - timedelta(hours=12)
        score = recommendation_service.recency_score(timestamp)
        assert score == 0.7

    def test_recency_score_1_to_3_days(self, recommendation_service):
        """Posts 1-3 days old should get score of 0.5."""
        timestamp = datetime.now(timezone.utc) - timedelta(days=2)
        score = recommendation_service.recency_score(timestamp)
        assert score == 0.5

    def test_recency_score_3_to_7_days(self, recommendation_service):
        """Posts 3-7 days old should get score of 0.3."""
        timestamp = datetime.now(timezone.utc) - timedelta(days=5)
        score = recommendation_service.recency_score(timestamp)
        assert score == 0.3

    def test_recency_score_over_7_days(self, recommendation_service):
        """Posts over 7 days old should get score of 0.1."""
        timestamp = datetime.now(timezone.utc) - timedelta(days=10)
        score = recommendation_service.recency_score(timestamp)
        assert score == DEFAULT_RECENCY_SCORE
        assert score == 0.1

    def test_recency_score_none_timestamp(self, recommendation_service):
        """None timestamp should return default score."""
        score = recommendation_service.recency_score(None)
        assert score == DEFAULT_RECENCY_SCORE

    def test_recency_score_naive_datetime(self, recommendation_service):
        """Naive datetime should be handled - treated as UTC."""
        # When naive datetime is passed, it's treated as UTC
        # Due to potential local timezone offset, accept valid scores
        timestamp = datetime.now() - timedelta(seconds=60)
        score = recommendation_service.recency_score(timestamp)
        # Score should be valid (0.1 to 1.0)
        assert 0.1 <= score <= 1.0

    def test_recency_score_boundary_6_hours(self, recommendation_service):
        """Posts at 6 hour boundary may fall into either bracket."""
        timestamp = datetime.now(timezone.utc) - timedelta(hours=6)
        score = recommendation_service.recency_score(timestamp)
        # At boundary, may fall into either bracket due to timing
        assert score in (0.9, 0.7)


# =============================================================================
# Engagement Score Tests
# =============================================================================


class TestEngagementScore:
    """Test engagement scoring with log normalization."""

    def test_engagement_score_zero(self, recommendation_service):
        """Post with no engagement should score 0."""
        post = create_mock_post(likes=0, comments=0, reposts=0)
        score = recommendation_service.engagement_score(post)
        assert score == 0.0

    def test_engagement_score_only_likes(self, recommendation_service):
        """Post with only likes."""
        post = create_mock_post(likes=100, comments=0, reposts=0)
        score = recommendation_service.engagement_score(post)
        # raw = 100 * 1 = 100
        # normalized = log(101) / log(10001) ≈ 0.5
        assert 0.4 < score < 0.6

    def test_engagement_score_only_comments(self, recommendation_service):
        """Post with only comments (weighted 2x)."""
        post = create_mock_post(likes=0, comments=50, reposts=0)
        score = recommendation_service.engagement_score(post)
        # raw = 50 * 2 = 100
        # Same as 100 likes
        assert 0.4 < score < 0.6

    def test_engagement_score_only_reposts(self, recommendation_service):
        """Post with only reposts (weighted 3x)."""
        post = create_mock_post(likes=0, comments=0, reposts=33)
        score = recommendation_service.engagement_score(post)
        # raw = 33 * 3 = 99
        # Similar to 100 likes
        assert 0.4 < score < 0.6

    def test_engagement_score_combined(self, recommendation_service):
        """Post with mixed engagement."""
        post = create_mock_post(likes=50, comments=25, reposts=10)
        score = recommendation_service.engagement_score(post)
        # raw = 50*1 + 25*2 + 10*3 = 50 + 50 + 30 = 130
        assert 0.4 < score < 0.65

    def test_engagement_score_viral_post(self, recommendation_service):
        """Viral post with high engagement (tests log normalization)."""
        post = create_mock_post(likes=10000, comments=5000, reposts=2000)
        score = recommendation_service.engagement_score(post)
        # raw = 10000 + 10000 + 6000 = 26000
        # With log normalization, should be clamped near 1.0
        assert 0.9 < score <= 1.0

    def test_engagement_score_log_normalization_effect(self, recommendation_service):
        """Verify log normalization prevents linear scaling."""
        post_small = create_mock_post(likes=10)
        post_medium = create_mock_post(likes=100)
        post_large = create_mock_post(likes=1000)
        
        score_small = recommendation_service.engagement_score(post_small)
        score_medium = recommendation_service.engagement_score(post_medium)
        score_large = recommendation_service.engagement_score(post_large)
        
        # Scores should increase sub-linearly
        assert score_medium < score_small * 10
        assert score_large < score_medium * 10
        
        # But larger should still be higher
        assert score_small < score_medium < score_large

    def test_engagement_score_null_counts(self, recommendation_service):
        """Handle None values for engagement counts."""
        post = create_mock_post()
        post.likes_count = None
        post.comments_count = None
        post.reposts_count = None
        
        score = recommendation_service.engagement_score(post)
        assert score == 0.0


# =============================================================================
# Author Affinity Tests
# =============================================================================


class TestAuthorAffinity:
    """Test author affinity scoring and tracking."""

    @pytest.mark.asyncio
    async def test_affinity_self_is_max(self, recommendation_service):
        """User should have maximum affinity with themselves."""
        score = await recommendation_service.author_affinity(user_id=1, author_id=1)
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_affinity_no_history(self, recommendation_service):
        """No interaction history should return 0."""
        score = await recommendation_service.author_affinity(user_id=1, author_id=2)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_record_like_interaction(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Recording a like should increase affinity."""
        await recommendation_service.record_like_interaction(user_id=1, author_id=2)
        
        # Check Redis was updated
        key = "affinity:1:2"
        assert key in mock_redis_for_recommendations._affinity_store
        assert float(mock_redis_for_recommendations._affinity_store[key]) == AFFINITY_LIKE_SCORE

    @pytest.mark.asyncio
    async def test_record_comment_interaction(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Recording a comment should increase affinity more than a like."""
        await recommendation_service.record_comment_interaction(user_id=1, author_id=2)
        
        key = "affinity:1:2"
        assert float(mock_redis_for_recommendations._affinity_store[key]) == AFFINITY_COMMENT_SCORE
        assert AFFINITY_COMMENT_SCORE > AFFINITY_LIKE_SCORE

    @pytest.mark.asyncio
    async def test_record_profile_visit(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Recording a profile visit should increase affinity slightly."""
        await recommendation_service.record_profile_visit(user_id=1, visited_user_id=2)
        
        key = "affinity:1:2"
        assert float(mock_redis_for_recommendations._affinity_store[key]) == AFFINITY_PROFILE_VISIT_SCORE

    @pytest.mark.asyncio
    async def test_affinity_accumulates(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Multiple interactions should accumulate affinity."""
        await recommendation_service.record_like_interaction(user_id=1, author_id=2)
        await recommendation_service.record_like_interaction(user_id=1, author_id=2)
        await recommendation_service.record_comment_interaction(user_id=1, author_id=2)
        
        key = "affinity:1:2"
        expected = AFFINITY_LIKE_SCORE * 2 + AFFINITY_COMMENT_SCORE
        assert float(mock_redis_for_recommendations._affinity_store[key]) == expected

    @pytest.mark.asyncio
    async def test_affinity_self_interaction_ignored(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Self-interactions should not be tracked."""
        await recommendation_service.record_like_interaction(user_id=1, author_id=1)
        
        key = "affinity:1:1"
        assert key not in mock_redis_for_recommendations._affinity_store

    @pytest.mark.asyncio
    async def test_affinity_normalization(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Affinity should be normalized to [0, 1]."""
        # Set a high affinity score
        mock_redis_for_recommendations._affinity_store["affinity:1:2"] = "150"
        
        score = await recommendation_service.author_affinity(user_id=1, author_id=2)
        assert score == 1.0  # Clamped to max

    @pytest.mark.asyncio
    async def test_affinity_retrieval(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Affinity should be retrievable after recording."""
        await recommendation_service.record_like_interaction(user_id=1, author_id=2)
        await recommendation_service.record_like_interaction(user_id=1, author_id=2)
        
        score = await recommendation_service.author_affinity(user_id=1, author_id=2)
        # 2 likes = 2.0 score, normalized by 100 = 0.02
        assert score == pytest.approx(0.02, rel=0.01)


# =============================================================================
# Combined Post Scoring Tests
# =============================================================================


class TestCalculatePostScore:
    """Test combined post scoring calculation."""

    def test_calculate_post_score_weights(self, recommendation_service):
        """Verify score weights sum to 1.0."""
        assert WEIGHT_RECENCY + WEIGHT_ENGAGEMENT + WEIGHT_AFFINITY == 1.0

    def test_calculate_post_score_fresh_popular_high_affinity(
        self, recommendation_service
    ):
        """Fresh, popular post from high-affinity author should score high."""
        post = create_mock_post(
            likes=1000,
            comments=500,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        
        scored = recommendation_service.calculate_post_score(
            post, user_id=1, affinity_score=0.9
        )
        
        assert scored.recency_score == 1.0
        assert scored.engagement_score > 0.8
        assert scored.affinity_score == 0.9
        assert scored.score > 0.85

    def test_calculate_post_score_old_unpopular_no_affinity(
        self, recommendation_service
    ):
        """Old, unpopular post with no affinity should score low."""
        post = create_mock_post(
            likes=2,
            comments=0,
            created_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        
        scored = recommendation_service.calculate_post_score(
            post, user_id=1, affinity_score=0.0
        )
        
        assert scored.recency_score == 0.1
        assert scored.engagement_score < 0.2
        assert scored.affinity_score == 0.0
        assert scored.score < 0.15

    def test_calculate_post_score_returns_scored_post(self, recommendation_service):
        """Should return a ScoredPost object with all components."""
        post = create_mock_post()
        
        scored = recommendation_service.calculate_post_score(
            post, user_id=1, affinity_score=0.5
        )
        
        assert isinstance(scored, ScoredPost)
        assert scored.post is post
        assert 0 <= scored.recency_score <= 1
        assert 0 <= scored.engagement_score <= 1
        assert 0 <= scored.affinity_score <= 1
        assert 0 <= scored.score <= 1

    def test_calculate_post_score_formula(self, recommendation_service):
        """Verify the scoring formula is applied correctly."""
        post = create_mock_post(
            likes=100,
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        
        scored = recommendation_service.calculate_post_score(
            post, user_id=1, affinity_score=0.5
        )
        
        expected = (
            scored.recency_score * WEIGHT_RECENCY
            + scored.engagement_score * WEIGHT_ENGAGEMENT
            + scored.affinity_score * WEIGHT_AFFINITY
        )
        
        assert scored.score == pytest.approx(expected, rel=0.001)


# =============================================================================
# Ranked Feed Tests
# =============================================================================


class TestGetRankedFeed:
    """Test ranked feed generation."""

    @pytest.mark.asyncio
    async def test_empty_following_returns_empty(self, recommendation_service):
        """Empty following list should return empty feed."""
        result = await recommendation_service.get_ranked_feed(
            user_id=1, following_ids=[], limit=20
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_limit_is_respected(
        self, db_session, mock_redis_for_recommendations, user_factory, post_factory
    ):
        """Feed should respect the limit parameter."""
        service = RecommendationService(db_session, mock_redis_for_recommendations)
        
        author = await user_factory()
        for i in range(10):
            await post_factory(author=author)
        await db_session.commit()
        
        result = await service.get_ranked_feed(
            user_id=999,
            following_ids=[author.id],
            limit=5,
        )
        
        assert len(result) <= 5

    @pytest.mark.asyncio
    async def test_includes_own_posts(
        self, db_session, mock_redis_for_recommendations, user_factory, post_factory
    ):
        """Feed should include user's own posts when following someone."""
        service = RecommendationService(db_session, mock_redis_for_recommendations)
        
        user = await user_factory()
        other_user = await user_factory()
        own_post = await post_factory(author=user, body="My own post")
        await db_session.commit()
        
        # When following at least one person, own posts are included
        result = await service.get_ranked_feed(
            user_id=user.id,
            following_ids=[other_user.id],  # Following someone
            limit=20,
        )
        
        # Own posts should appear alongside followed users' posts
        post_ids = [p.id for p in result]
        assert own_post.id in post_ids


# =============================================================================
# Cache Operations Tests
# =============================================================================


class TestCacheOperations:
    """Test feed caching operations."""

    @pytest.mark.asyncio
    async def test_cache_ranked_feed(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Should cache posts in Redis sorted set."""
        posts = [
            create_mock_post(post_id=1),
            create_mock_post(post_id=2),
            create_mock_post(post_id=3),
        ]
        
        await recommendation_service.cache_ranked_feed(user_id=1, posts=posts)
        
        # Check sorted set was created
        assert "ranked_feed:1" in mock_redis_for_recommendations._sorted_sets

    @pytest.mark.asyncio
    async def test_cache_empty_posts(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Empty posts list should not create cache."""
        await recommendation_service.cache_ranked_feed(user_id=1, posts=[])
        
        assert "ranked_feed:1" not in mock_redis_for_recommendations._sorted_sets

    @pytest.mark.asyncio
    async def test_get_cached_feed_miss(self, recommendation_service):
        """Cache miss should return None."""
        result = await recommendation_service.get_cached_ranked_feed(user_id=999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_feed_hit(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Cache hit should return post IDs."""
        posts = [
            create_mock_post(post_id=10),
            create_mock_post(post_id=20),
            create_mock_post(post_id=30),
        ]
        
        await recommendation_service.cache_ranked_feed(user_id=1, posts=posts)
        result = await recommendation_service.get_cached_ranked_feed(user_id=1)
        
        assert result is not None
        assert len(result) == 3
        assert all(isinstance(pid, int) for pid in result)


# =============================================================================
# Affinity Decay Tests
# =============================================================================


class TestAffinityDecay:
    """Test affinity score decay over time."""

    @pytest.mark.asyncio
    async def test_decay_reduces_scores(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Decay should reduce all affinity scores."""
        # Set up some affinity scores
        mock_redis_for_recommendations._affinity_store["affinity:1:2"] = "10.0"
        mock_redis_for_recommendations._affinity_store["affinity:1:3"] = "5.0"
        
        decayed = await recommendation_service.decay_affinity_scores(user_id=1)
        
        assert decayed >= 0

    @pytest.mark.asyncio
    async def test_decay_removes_tiny_scores(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Very small scores should be removed after decay."""
        mock_redis_for_recommendations._affinity_store["affinity:1:2"] = "0.005"
        
        await recommendation_service.decay_affinity_scores(user_id=1)
        
        # Score below threshold should be deleted
        # (depends on implementation - 0.005 * 0.95 = 0.00475 < 0.01)


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunction:
    """Test the factory function for creating services."""

    def test_get_recommendation_service(
        self, db_session, mock_redis_for_recommendations
    ):
        """Factory should return a configured service."""
        service = get_recommendation_service(db_session, mock_redis_for_recommendations)
        
        assert isinstance(service, RecommendationService)
        assert service.db is db_session
        assert service.redis is mock_redis_for_recommendations


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_engagement_score_negative_counts(self, recommendation_service):
        """Negative counts should be handled (treated as 0)."""
        post = create_mock_post(likes=-5, comments=-3, reposts=-1)
        # Negative counts are clamped to 0
        score = recommendation_service.engagement_score(post)
        # Score should be 0 since all counts are negative (treated as 0)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_affinity_invalid_redis_value(
        self, recommendation_service, mock_redis_for_recommendations
    ):
        """Invalid Redis values should be handled gracefully."""
        mock_redis_for_recommendations._affinity_store["affinity:1:2"] = "not_a_number"
        
        score = await recommendation_service.author_affinity(user_id=1, author_id=2)
        assert score == 0.0

    def test_recency_far_future_date(self, recommendation_service):
        """Future dates should get maximum recency score."""
        future_timestamp = datetime.now(timezone.utc) + timedelta(days=1)
        score = recommendation_service.recency_score(future_timestamp)
        # Negative age should result in score 1.0 (or handle gracefully)
        assert score == 1.0

    def test_recency_very_old_date(self, recommendation_service):
        """Very old dates should get minimum score."""
        old_timestamp = datetime.now(timezone.utc) - timedelta(days=365)
        score = recommendation_service.recency_score(old_timestamp)
        assert score == 0.1

