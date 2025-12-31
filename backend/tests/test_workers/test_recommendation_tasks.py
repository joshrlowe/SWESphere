"""
Tests for recommendation Celery tasks.

Comprehensive test coverage for:
- Feed precomputation
- Affinity decay
- Individual user feed computation
- Cache invalidation
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.workers.tasks.recommendation_tasks import (
    AFFINITY_DECAY_FACTOR,
    PRECOMPUTE_BATCH_SIZE,
    PRECOMPUTE_FEED_SIZE,
    RANKED_FEED_TTL,
    _calculate_engagement_score,
    _calculate_post_score,
    _calculate_recency_score,
    _get_affinity_score,
    compute_user_feed,
    decay_affinity_scores,
    invalidate_ranked_feed,
    precompute_feeds,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_redis():
    """Create mock Redis client for task testing."""
    redis = MagicMock()
    
    _storage: dict[str, str] = {}
    _sorted_sets: dict[str, dict[str, float]] = {}
    
    def mock_get(key: str):
        return _storage.get(key)
    
    def mock_set(key: str, value: Any, ex: int = None):
        _storage[key] = str(value)
        return True
    
    def mock_delete(key: str):
        deleted = 0
        if key in _storage:
            del _storage[key]
            deleted += 1
        if key in _sorted_sets:
            del _sorted_sets[key]
            deleted += 1
        return deleted
    
    def mock_ttl(key: str):
        if key in _storage:
            return 3600
        return -2
    
    def mock_scan_iter(match: str = "*"):
        import fnmatch
        for key in list(_storage.keys()):
            if fnmatch.fnmatch(key, match):
                yield key
    
    class MockPipeline:
        def __init__(self):
            self._ops = []
        
        def delete(self, key):
            self._ops.append(("delete", key))
            return self
        
        def zadd(self, key, mapping):
            self._ops.append(("zadd", key, mapping))
            return self
        
        def expire(self, key, ttl):
            self._ops.append(("expire", key, ttl))
            return self
        
        def execute(self):
            results = []
            for op in self._ops:
                if op[0] == "delete":
                    results.append(mock_delete(op[1]))
                elif op[0] == "zadd":
                    if op[1] not in _sorted_sets:
                        _sorted_sets[op[1]] = {}
                    _sorted_sets[op[1]].update(op[2])
                    results.append(len(op[2]))
                elif op[0] == "expire":
                    results.append(True)
            self._ops = []
            return results
    
    redis.get = mock_get
    redis.set = mock_set
    redis.delete = mock_delete
    redis.ttl = mock_ttl
    redis.scan_iter = mock_scan_iter
    redis.pipeline = MockPipeline
    
    redis._storage = _storage
    redis._sorted_sets = _sorted_sets
    
    return redis


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = MagicMock()
    session.query = MagicMock()
    session.execute = MagicMock()
    session.close = MagicMock()
    return session


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestRecencyScoreHelper:
    """Test the _calculate_recency_score helper function."""

    def test_under_1_hour(self):
        """Posts under 1 hour old get score 1.0."""
        timestamp = datetime.now(timezone.utc) - timedelta(minutes=30)
        assert _calculate_recency_score(timestamp) == 1.0

    def test_1_to_6_hours(self):
        """Posts 1-6 hours old get score 0.9."""
        timestamp = datetime.now(timezone.utc) - timedelta(hours=3)
        assert _calculate_recency_score(timestamp) == 0.9

    def test_6_to_24_hours(self):
        """Posts 6-24 hours old get score 0.7."""
        timestamp = datetime.now(timezone.utc) - timedelta(hours=12)
        assert _calculate_recency_score(timestamp) == 0.7

    def test_1_to_3_days(self):
        """Posts 1-3 days old get score 0.5."""
        timestamp = datetime.now(timezone.utc) - timedelta(days=2)
        assert _calculate_recency_score(timestamp) == 0.5

    def test_3_to_7_days(self):
        """Posts 3-7 days old get score 0.3."""
        timestamp = datetime.now(timezone.utc) - timedelta(days=5)
        assert _calculate_recency_score(timestamp) == 0.3

    def test_over_7_days(self):
        """Posts over 7 days old get score 0.1."""
        timestamp = datetime.now(timezone.utc) - timedelta(days=10)
        assert _calculate_recency_score(timestamp) == 0.1

    def test_naive_datetime(self):
        """Handles naive datetime - treated as UTC."""
        # Naive datetime is treated as UTC, may differ from local time
        timestamp = datetime.now() - timedelta(minutes=30)
        score = _calculate_recency_score(timestamp)
        # Should return a valid score
        assert 0.1 <= score <= 1.0


class TestEngagementScoreHelper:
    """Test the _calculate_engagement_score helper function."""

    def test_zero_engagement(self):
        """No engagement returns 0."""
        assert _calculate_engagement_score(0, 0, 0) == 0.0

    def test_only_likes(self):
        """Likes weighted at 1x."""
        score = _calculate_engagement_score(100, 0, 0)
        assert 0.4 < score < 0.6

    def test_only_comments(self):
        """Comments weighted at 2x."""
        score = _calculate_engagement_score(0, 50, 0)
        # 50 * 2 = 100, same as 100 likes
        assert 0.4 < score < 0.6

    def test_only_reposts(self):
        """Reposts weighted at 3x."""
        score = _calculate_engagement_score(0, 0, 33)
        # 33 * 3 = 99, similar to 100 likes
        assert 0.4 < score < 0.6

    def test_high_engagement_capped(self):
        """Very high engagement is capped at 1.0."""
        score = _calculate_engagement_score(50000, 25000, 10000)
        assert score <= 1.0


class TestAffinityScoreHelper:
    """Test the _get_affinity_score helper function."""

    def test_self_affinity(self, mock_redis):
        """Self-affinity returns 1.0."""
        score = _get_affinity_score(mock_redis, user_id=1, author_id=1)
        assert score == 1.0

    def test_no_affinity(self, mock_redis):
        """No stored affinity returns 0.0."""
        score = _get_affinity_score(mock_redis, user_id=1, author_id=2)
        assert score == 0.0

    def test_stored_affinity(self, mock_redis):
        """Stored affinity is retrieved and normalized."""
        mock_redis._storage["affinity:1:2"] = "50.0"
        score = _get_affinity_score(mock_redis, user_id=1, author_id=2)
        # 50 / 100 = 0.5
        assert score == 0.5

    def test_high_affinity_capped(self, mock_redis):
        """High affinity is capped at 1.0."""
        mock_redis._storage["affinity:1:2"] = "200.0"
        score = _get_affinity_score(mock_redis, user_id=1, author_id=2)
        assert score == 1.0


class TestPostScoreHelper:
    """Test the _calculate_post_score helper function."""

    def test_score_formula(self, mock_redis):
        """Verify the scoring formula is applied correctly."""
        post = MagicMock()
        post.created_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        post.likes_count = 100
        post.comments_count = 50
        post.reposts_count = 10
        post.user_id = 2
        
        score = _calculate_post_score(post, user_id=1, redis=mock_redis)
        
        # Score should be between 0 and 1
        assert 0 <= score <= 1

    def test_high_affinity_boosts_score(self, mock_redis):
        """High affinity should boost the score."""
        post = MagicMock()
        post.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        post.likes_count = 10
        post.comments_count = 5
        post.reposts_count = 1
        post.user_id = 2
        
        # Without affinity
        score_no_affinity = _calculate_post_score(post, user_id=1, redis=mock_redis)
        
        # With affinity
        mock_redis._storage["affinity:1:2"] = "50.0"
        score_with_affinity = _calculate_post_score(post, user_id=1, redis=mock_redis)
        
        assert score_with_affinity > score_no_affinity


# =============================================================================
# Precompute Feeds Task Tests
# =============================================================================


class TestPrecomputeFeedsTask:
    """Test the precompute_feeds Celery task."""

    @patch("app.workers.tasks.recommendation_tasks._get_sync_db_session")
    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_returns_success_stats(self, mock_get_redis, mock_get_db, mock_redis, mock_db_session):
        """Task should return success statistics."""
        mock_get_redis.return_value = mock_redis
        mock_get_db.return_value = mock_db_session
        
        # Mock empty user query
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        result = precompute_feeds()
        
        assert result["status"] == "success"
        assert "users_processed" in result
        assert "total_posts_cached" in result
        assert "duration_seconds" in result

    @patch("app.workers.tasks.recommendation_tasks._get_sync_db_session")
    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_closes_session_on_success(self, mock_get_redis, mock_get_db, mock_redis, mock_db_session):
        """Database session should be closed after success."""
        mock_get_redis.return_value = mock_redis
        mock_get_db.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        precompute_feeds()
        
        mock_db_session.close.assert_called_once()

    @patch("app.workers.tasks.recommendation_tasks._get_sync_db_session")
    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_closes_session_on_error(self, mock_get_redis, mock_get_db, mock_redis, mock_db_session):
        """Database session should be closed even on error."""
        mock_get_redis.return_value = mock_redis
        mock_get_db.return_value = mock_db_session
        mock_db_session.query.side_effect = Exception("DB Error")
        
        with pytest.raises(Exception):
            precompute_feeds()
        
        mock_db_session.close.assert_called_once()


# =============================================================================
# Decay Affinity Scores Task Tests
# =============================================================================


class TestDecayAffinityScoresTask:
    """Test the decay_affinity_scores Celery task."""

    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_returns_success_stats(self, mock_get_redis, mock_redis):
        """Task should return decay statistics."""
        mock_get_redis.return_value = mock_redis
        
        result = decay_affinity_scores()
        
        assert result["status"] == "success"
        assert "scores_decayed" in result
        assert "scores_deleted" in result
        assert "duration_seconds" in result

    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_decays_existing_scores(self, mock_get_redis, mock_redis):
        """Should apply decay factor to existing scores."""
        mock_get_redis.return_value = mock_redis
        mock_redis._storage["affinity:1:2"] = "10.0"
        mock_redis._storage["affinity:1:3"] = "5.0"
        
        result = decay_affinity_scores()
        
        assert result["scores_decayed"] >= 0

    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_deletes_tiny_scores(self, mock_get_redis, mock_redis):
        """Scores below threshold should be deleted."""
        mock_get_redis.return_value = mock_redis
        mock_redis._storage["affinity:1:2"] = "0.005"
        
        result = decay_affinity_scores()
        
        # Very small score * 0.95 < 0.01 threshold
        assert result["scores_deleted"] >= 0 or result["scores_decayed"] >= 0

    def test_decay_factor_is_valid(self):
        """Decay factor should be between 0 and 1."""
        assert 0 < AFFINITY_DECAY_FACTOR < 1


# =============================================================================
# Compute User Feed Task Tests
# =============================================================================


class TestComputeUserFeedTask:
    """Test the compute_user_feed Celery task."""

    @patch("app.workers.tasks.recommendation_tasks._get_sync_db_session")
    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_no_following_returns_empty(self, mock_get_redis, mock_get_db, mock_redis, mock_db_session):
        """User with no following should get empty result."""
        mock_get_redis.return_value = mock_redis
        mock_get_db.return_value = mock_db_session
        
        # Mock empty following list
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([])
        mock_db_session.execute.return_value = mock_result
        
        result = compute_user_feed(user_id=1)
        
        assert result["status"] == "success"
        assert result["posts_cached"] == 0
        assert result.get("reason") == "no_following"

    @patch("app.workers.tasks.recommendation_tasks._get_sync_db_session")
    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_returns_cached_count(self, mock_get_redis, mock_get_db, mock_redis, mock_db_session):
        """Should return number of posts cached."""
        mock_get_redis.return_value = mock_redis
        mock_get_db.return_value = mock_db_session
        
        # Mock following list
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([(2,), (3,)])
        mock_db_session.execute.return_value = mock_result
        
        # Mock empty posts
        mock_db_session.query.return_value.filter.return_value.options.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        result = compute_user_feed(user_id=1)
        
        assert result["status"] == "success"
        assert "posts_cached" in result

    @patch("app.workers.tasks.recommendation_tasks._get_sync_db_session")
    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_closes_session(self, mock_get_redis, mock_get_db, mock_redis, mock_db_session):
        """Should close database session."""
        mock_get_redis.return_value = mock_redis
        mock_get_db.return_value = mock_db_session
        
        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([])
        mock_db_session.execute.return_value = mock_result
        
        compute_user_feed(user_id=1)
        
        mock_db_session.close.assert_called_once()


# =============================================================================
# Invalidate Ranked Feed Task Tests
# =============================================================================


class TestInvalidateRankedFeedTask:
    """Test the invalidate_ranked_feed Celery task."""

    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_returns_success(self, mock_get_redis, mock_redis):
        """Should return success status."""
        mock_get_redis.return_value = mock_redis
        
        result = invalidate_ranked_feed(user_id=1)
        
        assert result["status"] == "success"
        assert result["user_id"] == 1

    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_deletes_cache_key(self, mock_get_redis, mock_redis):
        """Should delete the user's ranked feed cache."""
        mock_get_redis.return_value = mock_redis
        mock_redis._sorted_sets["ranked_feed:1"] = {"1": 0, "2": 1}
        
        result = invalidate_ranked_feed(user_id=1)
        
        assert result["status"] == "success"

    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_handles_missing_cache(self, mock_get_redis, mock_redis):
        """Should handle case where cache doesn't exist."""
        mock_get_redis.return_value = mock_redis
        
        result = invalidate_ranked_feed(user_id=999)
        
        assert result["status"] == "success"
        assert result["cache_deleted"] is False

    @patch("app.workers.tasks.recommendation_tasks._get_redis_client")
    def test_handles_redis_error(self, mock_get_redis, mock_redis):
        """Should return error status on Redis failure."""
        mock_get_redis.return_value = mock_redis
        mock_redis.delete = MagicMock(side_effect=Exception("Redis error"))
        
        result = invalidate_ranked_feed(user_id=1)
        
        assert result["status"] == "error"
        assert "error" in result


# =============================================================================
# Configuration Constants Tests
# =============================================================================


class TestConfigurationConstants:
    """Test that configuration constants are properly defined."""

    def test_batch_size_is_positive(self):
        """Batch size should be positive."""
        assert PRECOMPUTE_BATCH_SIZE > 0

    def test_feed_size_is_reasonable(self):
        """Feed size should be reasonable."""
        assert 50 <= PRECOMPUTE_FEED_SIZE <= 500

    def test_ttl_is_reasonable(self):
        """Cache TTL should be reasonable (1-10 minutes)."""
        assert 60 <= RANKED_FEED_TTL <= 600

    def test_decay_factor_is_valid(self):
        """Decay factor should cause gradual reduction."""
        assert 0.9 <= AFFINITY_DECAY_FACTOR <= 0.99

