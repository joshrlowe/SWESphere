"""
Integration tests for caching in services.

Tests that PostService and UserService properly use caching:
- Cache-aside pattern for reads
- Write-through for counters
- Cache invalidation on updates
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.cache_service import CacheService
from app.services.cache_invalidation import CacheInvalidator
from app.services.post_service import PostService
from app.services.user_service import UserService
from app.schemas.post import PostCreate
from app.core.redis_keys import CacheKeys


class TestPostServiceCaching:
    """Test caching integration in PostService."""

    @pytest.mark.asyncio
    async def test_get_home_feed_uses_cache_on_hit(
        self, post_repo, user_repo, mock_redis_full
    ):
        """Should return cached data on cache hit."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = PostService(
            post_repo=post_repo,
            user_repo=user_repo,
            redis=mock_redis_full,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        # Pre-populate cache
        cached_data = {
            "items": [{"id": 1, "body": "Cached post"}],
            "total": 1,
            "page": 1,
            "per_page": 20,
            "pages": 1,
            "has_next": False,
            "has_prev": False,
        }
        import json
        cache_key = CacheKeys.home_feed_page(user_id=1, page=1, per_page=20)
        mock_redis_full._storage[cache_key] = json.dumps(cached_data)
        
        result = await service.get_home_feed(user_id=1, page=1, per_page=20)
        
        # Should return cached data
        assert result.items == [{"id": 1, "body": "Cached post"}]
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_get_home_feed_populates_cache_on_miss(
        self, post_repo, user_repo, user_factory, post_factory, mock_redis_full
    ):
        """Should cache result on cache miss."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = PostService(
            post_repo=post_repo,
            user_repo=user_repo,
            redis=mock_redis_full,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        # Create test data
        user = await user_factory()
        post = await post_factory(author=user)
        
        cache_key = CacheKeys.home_feed_page(user_id=user.id, page=1, per_page=20)
        assert cache_key not in mock_redis_full._storage
        
        result = await service.get_home_feed(user_id=user.id, page=1, per_page=20)
        
        # Cache should be populated
        assert cache_key in mock_redis_full._storage
        assert result.total >= 1

    @pytest.mark.asyncio
    async def test_get_explore_feed_uses_cache(
        self, post_repo, user_repo, mock_redis_full
    ):
        """Should use cache for explore feed."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = PostService(
            post_repo=post_repo,
            user_repo=user_repo,
            redis=mock_redis_full,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        # Pre-populate cache
        import json
        cache_key = CacheKeys.explore_feed_page(page=1, per_page=20)
        mock_redis_full._storage[cache_key] = json.dumps({
            "items": [{"id": 2, "body": "Explore post"}],
            "total": 1,
            "page": 1,
            "per_page": 20,
            "pages": 1,
            "has_next": False,
            "has_prev": False,
        })
        
        result = await service.get_explore_feed(page=1, per_page=20)
        
        assert result.items == [{"id": 2, "body": "Explore post"}]

    @pytest.mark.asyncio
    async def test_like_post_updates_cache_counter(
        self, post_repo, user_repo, user_factory, post_factory, mock_redis_full
    ):
        """Should increment like counter in cache on like."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = PostService(
            post_repo=post_repo,
            user_repo=user_repo,
            redis=mock_redis_full,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        # Create test data
        user = await user_factory()
        author = await user_factory()
        post = await post_factory(author=author)
        
        # Initialize counter
        mock_redis_full._storage[CacheKeys.post_likes_count(post.id)] = "5"
        
        await service.like_post(user_id=user.id, post_id=post.id)
        
        # Counter should be incremented
        assert mock_redis_full._storage[CacheKeys.post_likes_count(post.id)] == "6"

    @pytest.mark.asyncio
    async def test_like_post_adds_to_likers_set(
        self, post_repo, user_repo, user_factory, post_factory, mock_redis_full
    ):
        """Should add user to likers set on like."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = PostService(
            post_repo=post_repo,
            user_repo=user_repo,
            redis=mock_redis_full,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        user = await user_factory()
        author = await user_factory()
        post = await post_factory(author=author)
        
        await service.like_post(user_id=user.id, post_id=post.id)
        
        # User should be in likers set
        assert str(user.id) in mock_redis_full._sets[CacheKeys.post_likers(post.id)]

    @pytest.mark.asyncio
    async def test_unlike_post_updates_cache_counter(
        self, post_repo, user_repo, user_factory, post_factory, mock_redis_full, db_session
    ):
        """Should decrement like counter in cache on unlike."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = PostService(
            post_repo=post_repo,
            user_repo=user_repo,
            redis=mock_redis_full,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        user = await user_factory()
        author = await user_factory()
        post = await post_factory(author=author)
        
        # First like the post
        await service.like_post(user_id=user.id, post_id=post.id)
        await db_session.commit()
        
        # Initialize counter
        mock_redis_full._storage[CacheKeys.post_likes_count(post.id)] = "6"
        
        # Now unlike
        await service.unlike_post(user_id=user.id, post_id=post.id)
        
        # Counter should be decremented
        assert mock_redis_full._storage[CacheKeys.post_likes_count(post.id)] == "5"

    @pytest.mark.asyncio
    async def test_is_liked_uses_cache(
        self, post_repo, user_repo, user_factory, post_factory, mock_redis_full
    ):
        """Should check cache for like status."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = PostService(
            post_repo=post_repo,
            user_repo=user_repo,
            redis=mock_redis_full,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        user = await user_factory()
        author = await user_factory()
        post = await post_factory(author=author)
        
        # Simulate cached like status
        mock_redis_full._sets[CacheKeys.post_likers(post.id)] = {str(user.id)}
        
        result = await service.is_liked(user_id=user.id, post_id=post.id)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_get_like_count_uses_cache(
        self, post_repo, user_repo, user_factory, post_factory, mock_redis_full
    ):
        """Should return cached like count."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = PostService(
            post_repo=post_repo,
            user_repo=user_repo,
            redis=mock_redis_full,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        user = await user_factory()
        post = await post_factory(author=user)
        
        # Set cached count
        mock_redis_full._storage[CacheKeys.post_likes_count(post.id)] = "42"
        
        result = await service.get_like_count(post_id=post.id)
        
        assert result == 42


class TestUserServiceCaching:
    """Test caching integration in UserService."""

    @pytest.mark.asyncio
    async def test_get_user_by_username_uses_cache(
        self, user_repo, user_factory, mock_redis_full
    ):
        """Should use cached username lookup."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = UserService(
            user_repo=user_repo,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        # Create user
        user = await user_factory(username="cacheduser")
        
        # Cache the username lookup
        mock_redis_full._storage[CacheKeys.user_by_username("cacheduser")] = str(user.id)
        
        result = await service.get_user_by_username("cacheduser")
        
        assert result.id == user.id

    @pytest.mark.asyncio
    async def test_get_user_by_username_populates_cache(
        self, user_repo, user_factory, mock_redis_full
    ):
        """Should cache username lookup on miss."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = UserService(
            user_repo=user_repo,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        user = await user_factory(username="newuser")
        
        # Cache should be empty
        assert CacheKeys.user_by_username("newuser") not in mock_redis_full._storage
        
        await service.get_user_by_username("newuser")
        
        # Cache should be populated
        assert CacheKeys.user_by_username("newuser") in mock_redis_full._storage

    @pytest.mark.asyncio
    async def test_cache_user_profile_stores_data(
        self, user_repo, user_factory, mock_redis_full
    ):
        """Should cache user profile data."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = UserService(
            user_repo=user_repo,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        user = await user_factory(username="profileuser", display_name="Profile User")
        
        await service.cache_user_profile(user)
        
        # Profile should be cached
        import json
        cached = json.loads(mock_redis_full._storage[CacheKeys.user(user.id)])
        assert cached["username"] == "profileuser"
        assert cached["display_name"] == "Profile User"

    @pytest.mark.asyncio
    async def test_get_user_profile_cached_returns_data(
        self, user_repo, user_factory, mock_redis_full
    ):
        """Should return cached profile data."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = UserService(
            user_repo=user_repo,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        # Cache profile data
        import json
        mock_redis_full._storage[CacheKeys.user(123)] = json.dumps({
            "id": 123,
            "username": "cachedprofile",
            "followers_count": 1000,
        })
        
        result = await service.get_user_profile_cached(123)
        
        assert result is not None
        assert result["username"] == "cachedprofile"
        assert result["followers_count"] == 1000

    @pytest.mark.asyncio
    async def test_follow_user_updates_cache_counters(
        self, user_repo, user_factory, mock_redis_full, db_session
    ):
        """Should update follower/following counters on follow."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = UserService(
            user_repo=user_repo,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        follower = await user_factory()
        followed = await user_factory()
        await db_session.commit()
        
        # Initialize counters
        mock_redis_full._storage[CacheKeys.user_followers_count(followed.id)] = "10"
        mock_redis_full._storage[CacheKeys.user_following_count(follower.id)] = "5"
        
        await service.follow_user(follower.id, followed.id)
        
        # Counters should be updated
        assert mock_redis_full._storage[CacheKeys.user_followers_count(followed.id)] == "11"
        assert mock_redis_full._storage[CacheKeys.user_following_count(follower.id)] == "6"

    @pytest.mark.asyncio
    async def test_unfollow_user_updates_cache_counters(
        self, user_repo, user_factory, mock_redis_full, db_session
    ):
        """Should update follower/following counters on unfollow."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = UserService(
            user_repo=user_repo,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        follower = await user_factory()
        followed = await user_factory()
        await db_session.commit()
        
        # First follow
        await service.follow_user(follower.id, followed.id)
        await db_session.commit()
        
        # Set counters
        mock_redis_full._storage[CacheKeys.user_followers_count(followed.id)] = "11"
        mock_redis_full._storage[CacheKeys.user_following_count(follower.id)] = "6"
        
        await service.unfollow_user(follower.id, followed.id)
        
        # Counters should be decremented
        assert mock_redis_full._storage[CacheKeys.user_followers_count(followed.id)] == "10"
        assert mock_redis_full._storage[CacheKeys.user_following_count(follower.id)] == "5"

    @pytest.mark.asyncio
    async def test_get_followers_count_uses_cache(
        self, user_repo, user_factory, mock_redis_full
    ):
        """Should return cached follower count."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = UserService(
            user_repo=user_repo,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        user = await user_factory()
        
        # Set cached count
        mock_redis_full._storage[CacheKeys.user_followers_count(user.id)] = "150"
        
        result = await service.get_followers_count(user.id)
        
        assert result == 150

    @pytest.mark.asyncio
    async def test_get_following_count_uses_cache(
        self, user_repo, user_factory, mock_redis_full
    ):
        """Should return cached following count."""
        cache = CacheService(mock_redis_full)
        invalidator = CacheInvalidator(cache)
        
        service = UserService(
            user_repo=user_repo,
            cache=cache,
            cache_invalidator=invalidator,
        )
        
        user = await user_factory()
        
        # Set cached count
        mock_redis_full._storage[CacheKeys.user_following_count(user.id)] = "75"
        
        result = await service.get_following_count(user.id)
        
        assert result == 75


class TestCacheWithoutRedis:
    """Test services work correctly without cache configured."""

    @pytest.mark.asyncio
    async def test_post_service_works_without_cache(
        self, post_repo, user_repo, user_factory, post_factory
    ):
        """PostService should work without cache."""
        service = PostService(
            post_repo=post_repo,
            user_repo=user_repo,
            redis=None,
            cache=None,
            cache_invalidator=None,
        )
        
        user = await user_factory()
        post = await post_factory(author=user)
        
        # Should work without cache
        result = await service.get_home_feed(user_id=user.id, page=1, per_page=20)
        
        assert result.total >= 1

    @pytest.mark.asyncio
    async def test_user_service_works_without_cache(
        self, user_repo, user_factory
    ):
        """UserService should work without cache."""
        service = UserService(
            user_repo=user_repo,
            cache=None,
            cache_invalidator=None,
        )
        
        user = await user_factory(username="nocacheuser")
        
        # Should work without cache
        result = await service.get_user_by_username("nocacheuser")
        
        assert result.username == "nocacheuser"

