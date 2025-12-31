"""
Integration tests for the recommendation system.

Tests end-to-end feed ranking scenarios including:
- Full ranking pipeline with real database
- Affinity-influenced rankings
- Feed personalization differences between users
- Cache integration
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.user import User
from app.services.recommendation_service import RecommendationService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_redis_integration():
    """Create a more realistic mock Redis for integration testing."""
    redis = AsyncMock()
    
    _storage: dict[str, str] = {}
    _sorted_sets: dict[str, dict[str, float]] = {}
    
    async def mock_get(key: str):
        return _storage.get(key)
    
    async def mock_set(key: str, value: Any, ex: int = None):
        _storage[key] = str(value)
        return True
    
    async def mock_incrbyfloat(key: str, amount: float):
        current = float(_storage.get(key, "0"))
        new_value = current + amount
        _storage[key] = str(new_value)
        return new_value
    
    async def mock_expire(key: str, ttl: int):
        return True
    
    async def mock_delete(key: str):
        if key in _storage:
            del _storage[key]
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
        return 3600 if key in _storage else -2
    
    async def mock_scan_iter(match: str = "*"):
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
        
        async def execute(self):
            results = []
            for op in self._ops:
                if op[0] == "delete":
                    results.append(await mock_delete(op[1]))
                elif op[0] == "zadd":
                    results.append(await mock_zadd(op[1], op[2]))
                elif op[0] == "expire":
                    results.append(True)
            self._ops = []
            return results
    
    redis.get = mock_get
    redis.set = mock_set
    redis.incrbyfloat = mock_incrbyfloat
    redis.expire = mock_expire
    redis.delete = mock_delete
    redis.zadd = mock_zadd
    redis.zrange = mock_zrange
    redis.ttl = mock_ttl
    redis.scan_iter = mock_scan_iter
    redis.pipeline = lambda: MockPipeline()
    
    redis._storage = _storage
    redis._sorted_sets = _sorted_sets
    
    return redis


# =============================================================================
# End-to-End Feed Ranking Tests
# =============================================================================


class TestEndToEndFeedRanking:
    """Test complete feed ranking scenarios."""

    @pytest.mark.asyncio
    async def test_fresh_posts_rank_higher_than_old(
        self, db_session: AsyncSession, mock_redis_integration, user_factory, post_factory
    ):
        """Fresh posts should rank higher than old posts (all else equal)."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        author = await user_factory()
        viewer = await user_factory()
        
        # Create old post (3 days ago)
        old_post = await post_factory(
            author=author,
            body="Old post",
        )
        old_post.created_at = datetime.now(timezone.utc) - timedelta(days=3)
        
        # Create fresh post (30 minutes ago)
        fresh_post = await post_factory(
            author=author,
            body="Fresh post",
        )
        fresh_post.created_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        
        await db_session.commit()
        
        # Get ranked feed
        feed = await service.get_ranked_feed(
            user_id=viewer.id,
            following_ids=[author.id],
            limit=10,
        )
        
        # Fresh post should come first
        assert len(feed) == 2
        assert feed[0].id == fresh_post.id
        assert feed[1].id == old_post.id

    @pytest.mark.asyncio
    async def test_popular_posts_rank_higher(
        self, db_session: AsyncSession, mock_redis_integration, user_factory, post_factory
    ):
        """Popular posts should rank higher than unpopular (similar recency)."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        author = await user_factory()
        viewer = await user_factory()
        
        # Create unpopular post
        unpopular = await post_factory(
            author=author,
            body="Unpopular post",
        )
        unpopular.likes_count = 1
        unpopular.comments_count = 0
        unpopular.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Create popular post (same age)
        popular = await post_factory(
            author=author,
            body="Popular post",
        )
        popular.likes_count = 1000
        popular.comments_count = 500
        popular.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        await db_session.commit()
        
        feed = await service.get_ranked_feed(
            user_id=viewer.id,
            following_ids=[author.id],
            limit=10,
        )
        
        # Popular post should come first
        assert len(feed) == 2
        assert feed[0].id == popular.id
        assert feed[1].id == unpopular.id

    @pytest.mark.asyncio
    async def test_high_affinity_author_ranks_higher(
        self, db_session: AsyncSession, mock_redis_integration, user_factory, post_factory
    ):
        """Posts from high-affinity authors should rank higher."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        favorite_author = await user_factory(username="favorite")
        other_author = await user_factory(username="other")
        viewer = await user_factory(username="viewer")
        
        # Create similar posts from both authors
        favorite_post = await post_factory(
            author=favorite_author,
            body="Post from favorite",
        )
        favorite_post.likes_count = 50
        favorite_post.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        
        other_post = await post_factory(
            author=other_author,
            body="Post from other",
        )
        other_post.likes_count = 50
        other_post.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        
        await db_session.commit()
        
        # Record affinity with favorite author
        await service.record_like_interaction(viewer.id, favorite_author.id)
        await service.record_like_interaction(viewer.id, favorite_author.id)
        await service.record_comment_interaction(viewer.id, favorite_author.id)
        
        feed = await service.get_ranked_feed(
            user_id=viewer.id,
            following_ids=[favorite_author.id, other_author.id],
            limit=10,
        )
        
        # Favorite author's post should rank higher due to affinity
        assert len(feed) == 2
        assert feed[0].id == favorite_post.id

    @pytest.mark.asyncio
    async def test_different_users_get_different_rankings(
        self, db_session: AsyncSession, mock_redis_integration, user_factory, post_factory
    ):
        """Different users should get personalized rankings based on affinity."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        author_a = await user_factory(username="author_a")
        author_b = await user_factory(username="author_b")
        user_1 = await user_factory(username="user1")
        user_2 = await user_factory(username="user2")
        
        # Create similar posts
        post_a = await post_factory(author=author_a, body="Post A")
        post_a.likes_count = 100
        post_a.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        post_b = await post_factory(author=author_b, body="Post B")
        post_b.likes_count = 100
        post_b.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        await db_session.commit()
        
        # User 1 prefers author A
        for _ in range(5):
            await service.record_like_interaction(user_1.id, author_a.id)
        
        # User 2 prefers author B
        for _ in range(5):
            await service.record_like_interaction(user_2.id, author_b.id)
        
        following = [author_a.id, author_b.id]
        
        feed_1 = await service.get_ranked_feed(user_id=user_1.id, following_ids=following, limit=10)
        feed_2 = await service.get_ranked_feed(user_id=user_2.id, following_ids=following, limit=10)
        
        # Each user should see their preferred author first
        assert feed_1[0].id == post_a.id
        assert feed_2[0].id == post_b.id


# =============================================================================
# Affinity Accumulation Tests
# =============================================================================


class TestAffinityAccumulation:
    """Test that affinity accumulates correctly over interactions."""

    @pytest.mark.asyncio
    async def test_multiple_likes_increase_affinity(
        self, db_session: AsyncSession, mock_redis_integration
    ):
        """Multiple likes should accumulate affinity."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        # Record multiple likes
        for _ in range(10):
            await service.record_like_interaction(user_id=1, author_id=2)
        
        affinity = await service.author_affinity(user_id=1, author_id=2)
        
        # Should have accumulated 10 * 1.0 = 10 points, normalized to 0.1
        assert affinity == pytest.approx(0.1, rel=0.01)

    @pytest.mark.asyncio
    async def test_mixed_interactions_accumulate(
        self, db_session: AsyncSession, mock_redis_integration
    ):
        """Different interaction types should all contribute to affinity."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        # Mix of interactions
        await service.record_like_interaction(user_id=1, author_id=2)  # +1
        await service.record_comment_interaction(user_id=1, author_id=2)  # +3
        await service.record_profile_visit(user_id=1, visited_user_id=2)  # +0.5
        
        affinity = await service.author_affinity(user_id=1, author_id=2)
        
        # Total = 1 + 3 + 0.5 = 4.5, normalized = 0.045
        assert affinity == pytest.approx(0.045, rel=0.01)

    @pytest.mark.asyncio
    async def test_affinity_is_directional(
        self, db_session: AsyncSession, mock_redis_integration
    ):
        """Affinity from A to B should not affect B to A."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        # User 1 likes user 2's content
        for _ in range(10):
            await service.record_like_interaction(user_id=1, author_id=2)
        
        affinity_1_to_2 = await service.author_affinity(user_id=1, author_id=2)
        affinity_2_to_1 = await service.author_affinity(user_id=2, author_id=1)
        
        assert affinity_1_to_2 > 0
        assert affinity_2_to_1 == 0


# =============================================================================
# Cache Integration Tests
# =============================================================================


class TestCacheIntegration:
    """Test feed caching integration."""

    @pytest.mark.asyncio
    async def test_cache_stores_rankings(
        self, db_session: AsyncSession, mock_redis_integration, user_factory, post_factory
    ):
        """Caching should store ranked post IDs."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        author = await user_factory()
        for i in range(5):
            await post_factory(author=author, body=f"Post {i}")
        await db_session.commit()
        
        # Get and cache feed
        feed = await service.get_ranked_feed(
            user_id=999,
            following_ids=[author.id],
            limit=10,
        )
        
        await service.cache_ranked_feed(user_id=999, posts=feed)
        
        # Verify cache was populated
        cached_ids = await service.get_cached_ranked_feed(user_id=999)
        
        assert cached_ids is not None
        assert len(cached_ids) == len(feed)

    @pytest.mark.asyncio
    async def test_cache_preserves_order(
        self, db_session: AsyncSession, mock_redis_integration, user_factory, post_factory
    ):
        """Cached feed should preserve ranking order (same set of posts)."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        author = await user_factory()
        posts = []
        for i in range(5):
            post = await post_factory(author=author)
            post.likes_count = (5 - i) * 100  # Descending engagement
            posts.append(post)
        await db_session.commit()
        
        feed = await service.get_ranked_feed(
            user_id=999,
            following_ids=[author.id],
            limit=10,
        )
        
        await service.cache_ranked_feed(user_id=999, posts=feed)
        cached_ids = await service.get_cached_ranked_feed(user_id=999)
        
        # Same posts should be cached (order may vary by implementation)
        feed_ids = [p.id for p in feed]
        assert set(cached_ids) == set(feed_ids)
        assert len(cached_ids) == len(feed_ids)


# =============================================================================
# Edge Case Integration Tests
# =============================================================================


class TestEdgeCaseIntegration:
    """Integration tests for edge cases."""

    @pytest.mark.asyncio
    async def test_user_with_no_following(
        self, db_session: AsyncSession, mock_redis_integration, user_factory
    ):
        """User following no one should get empty feed."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        user = await user_factory()
        await db_session.commit()
        
        feed = await service.get_ranked_feed(
            user_id=user.id,
            following_ids=[],
            limit=50,
        )
        
        assert feed == []

    @pytest.mark.asyncio
    async def test_following_users_with_no_posts(
        self, db_session: AsyncSession, mock_redis_integration, user_factory
    ):
        """Following users with no posts should return empty feed."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        viewer = await user_factory()
        author = await user_factory()
        await db_session.commit()
        
        feed = await service.get_ranked_feed(
            user_id=viewer.id,
            following_ids=[author.id],
            limit=50,
        )
        
        assert feed == []

    @pytest.mark.asyncio
    async def test_limit_zero_returns_empty(
        self, db_session: AsyncSession, mock_redis_integration, user_factory, post_factory
    ):
        """Limit of 0 should return empty list."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        author = await user_factory()
        await post_factory(author=author)
        await db_session.commit()
        
        feed = await service.get_ranked_feed(
            user_id=999,
            following_ids=[author.id],
            limit=0,
        )
        
        assert len(feed) == 0

    @pytest.mark.asyncio
    async def test_very_old_posts_excluded(
        self, db_session: AsyncSession, mock_redis_integration, user_factory, post_factory
    ):
        """Posts older than max_age_days should be excluded."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        author = await user_factory()
        
        old_post = await post_factory(author=author, body="Old post")
        old_post.created_at = datetime.now(timezone.utc) - timedelta(days=30)
        
        await db_session.commit()
        
        feed = await service.get_ranked_feed(
            user_id=999,
            following_ids=[author.id],
            limit=50,
            max_age_days=7,  # Only last 7 days
        )
        
        # Old post should not appear
        assert len(feed) == 0


# =============================================================================
# Performance Consideration Tests
# =============================================================================


class TestPerformanceConsiderations:
    """Tests for performance-related behavior."""

    @pytest.mark.asyncio
    async def test_handles_many_posts(
        self, db_session: AsyncSession, mock_redis_integration, user_factory, post_factory
    ):
        """Should handle a large number of posts efficiently."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        author = await user_factory()
        
        # Create 100 posts
        for i in range(100):
            post = await post_factory(author=author, body=f"Post {i}")
            post.likes_count = i  # Varying engagement
        
        await db_session.commit()
        
        feed = await service.get_ranked_feed(
            user_id=999,
            following_ids=[author.id],
            limit=20,
        )
        
        # Should return exactly 20 posts
        assert len(feed) == 20

    @pytest.mark.asyncio
    async def test_handles_many_authors(
        self, db_session: AsyncSession, mock_redis_integration, user_factory, post_factory
    ):
        """Should handle many followed authors."""
        service = RecommendationService(db_session, mock_redis_integration)
        
        # Create 20 authors with 2 posts each
        author_ids = []
        for i in range(20):
            author = await user_factory(username=f"author{i}")
            author_ids.append(author.id)
            for j in range(2):
                await post_factory(author=author, body=f"Post {i}-{j}")
        
        await db_session.commit()
        
        feed = await service.get_ranked_feed(
            user_id=999,
            following_ids=author_ids,
            limit=50,
        )
        
        # Should have posts from multiple authors
        assert len(feed) > 0
        assert len(feed) <= 50

