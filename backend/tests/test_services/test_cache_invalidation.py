"""
Tests for CacheInvalidator.

Covers:
- User cache invalidation
- Feed cache invalidation
- Post cache invalidation
- Event handlers (new post, follow/unfollow, like/unlike)
- Cache warming
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.redis_keys import CacheKeys
from app.services.cache_invalidation import CacheInvalidator


class TestUserInvalidation:
    """Test user cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_user_clears_profile_cache(
        self, cache_service, cache_invalidator, mock_redis_full
    ):
        """Should delete user profile cache."""
        user_id = 123
        mock_redis_full._storage[CacheKeys.user(user_id)] = '{"id": 123}'
        
        await cache_invalidator.invalidate_user(user_id)
        
        assert CacheKeys.user(user_id) not in mock_redis_full._storage

    @pytest.mark.asyncio
    async def test_invalidate_user_clears_username_lookup(
        self, cache_service, cache_invalidator, mock_redis_full
    ):
        """Should delete username lookup cache when username provided."""
        user_id = 123
        username = "testuser"
        mock_redis_full._storage[CacheKeys.user_by_username(username)] = "123"
        
        await cache_invalidator.invalidate_user(user_id, username)
        
        assert CacheKeys.user_by_username(username) not in mock_redis_full._storage

    @pytest.mark.asyncio
    async def test_invalidate_user_feeds_clears_all_feed_pages(
        self, cache_service, cache_invalidator, mock_redis_full
    ):
        """Should delete all paginated feed caches for user."""
        user_id = 1
        # Add multiple feed pages
        mock_redis_full._storage["home_feed:1:1:20"] = "data"
        mock_redis_full._storage["home_feed:1:2:20"] = "data"
        mock_redis_full._storage["home_feed:1:1:50"] = "data"
        mock_redis_full._storage["home_feed:2:1:20"] = "other user"
        
        await cache_invalidator.invalidate_user_feeds(user_id)
        
        # User 1's feeds should be deleted
        assert "home_feed:1:1:20" not in mock_redis_full._storage
        assert "home_feed:1:2:20" not in mock_redis_full._storage
        assert "home_feed:1:1:50" not in mock_redis_full._storage
        # User 2's feeds should remain
        assert "home_feed:2:1:20" in mock_redis_full._storage

    @pytest.mark.asyncio
    async def test_invalidate_followers_feeds_clears_all_follower_feeds(
        self, cache_invalidator, mock_redis_full
    ):
        """Should invalidate feeds for all followers."""
        user_id = 1
        follower_ids = [10, 20, 30]
        
        # Add feed caches for followers
        for fid in follower_ids:
            mock_redis_full._storage[f"home_feed:{fid}:1:20"] = "data"
        
        await cache_invalidator.invalidate_followers_feeds(user_id, follower_ids)
        
        # All follower feeds should be deleted
        for fid in follower_ids:
            assert f"home_feed:{fid}:1:20" not in mock_redis_full._storage


class TestPostInvalidation:
    """Test post cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_post_clears_post_cache(
        self, cache_invalidator, mock_redis_full
    ):
        """Should delete post cache."""
        post_id = 456
        mock_redis_full._storage[CacheKeys.post(post_id)] = '{"id": 456}'
        
        await cache_invalidator.invalidate_post(post_id)
        
        assert CacheKeys.post(post_id) not in mock_redis_full._storage

    @pytest.mark.asyncio
    async def test_invalidate_explore_feed_clears_all_pages(
        self, cache_invalidator, mock_redis_full
    ):
        """Should delete all explore feed pages."""
        mock_redis_full._storage["explore_feed:1:20"] = "data"
        mock_redis_full._storage["explore_feed:2:20"] = "data"
        mock_redis_full._storage["explore_feed:1:50"] = "data"
        
        await cache_invalidator.invalidate_explore_feed()
        
        assert "explore_feed:1:20" not in mock_redis_full._storage
        assert "explore_feed:2:20" not in mock_redis_full._storage
        assert "explore_feed:1:50" not in mock_redis_full._storage


class TestOnNewPost:
    """Test cache updates on new post creation."""

    @pytest.mark.asyncio
    async def test_on_new_post_invalidates_author_feed(
        self, cache_invalidator, mock_redis_full
    ):
        """Should invalidate author's feed cache."""
        author_id = 1
        mock_redis_full._storage[f"home_feed:{author_id}:1:20"] = "data"
        
        # Mock post object
        post = MagicMock()
        post.id = 100
        
        await cache_invalidator.on_new_post(post, author_id, follower_ids=[])
        
        assert f"home_feed:{author_id}:1:20" not in mock_redis_full._storage

    @pytest.mark.asyncio
    async def test_on_new_post_invalidates_follower_feeds(
        self, cache_invalidator, mock_redis_full
    ):
        """Should invalidate all follower feeds."""
        author_id = 1
        follower_ids = [10, 20]
        
        for fid in follower_ids:
            mock_redis_full._storage[f"home_feed:{fid}:1:20"] = "data"
        
        post = MagicMock()
        post.id = 100
        
        await cache_invalidator.on_new_post(post, author_id, follower_ids)
        
        for fid in follower_ids:
            assert f"home_feed:{fid}:1:20" not in mock_redis_full._storage

    @pytest.mark.asyncio
    async def test_on_new_post_invalidates_explore_feed(
        self, cache_invalidator, mock_redis_full
    ):
        """Should invalidate explore feed."""
        mock_redis_full._storage["explore_feed:1:20"] = "data"
        
        post = MagicMock()
        post.id = 100
        
        await cache_invalidator.on_new_post(post, author_id=1, follower_ids=[])
        
        assert "explore_feed:1:20" not in mock_redis_full._storage


class TestOnPostDelete:
    """Test cache updates on post deletion."""

    @pytest.mark.asyncio
    async def test_on_post_delete_clears_post_cache(
        self, cache_invalidator, mock_redis_full
    ):
        """Should delete the post cache."""
        post_id = 100
        mock_redis_full._storage[CacheKeys.post(post_id)] = '{"id": 100}'
        
        await cache_invalidator.on_post_delete(post_id, author_id=1, follower_ids=[])
        
        assert CacheKeys.post(post_id) not in mock_redis_full._storage

    @pytest.mark.asyncio
    async def test_on_post_delete_clears_like_data(
        self, cache_invalidator, mock_redis_full
    ):
        """Should delete like tracking data."""
        post_id = 100
        mock_redis_full._sets[CacheKeys.post_likers(post_id)] = {"1", "2", "3"}
        mock_redis_full._storage[CacheKeys.post_likes_count(post_id)] = "3"
        
        await cache_invalidator.on_post_delete(post_id, author_id=1, follower_ids=[])
        
        assert CacheKeys.post_likers(post_id) not in mock_redis_full._sets
        assert CacheKeys.post_likes_count(post_id) not in mock_redis_full._storage


class TestOnFollow:
    """Test cache updates on follow event."""

    @pytest.mark.asyncio
    async def test_on_follow_invalidates_follower_feed(
        self, cache_invalidator, mock_redis_full
    ):
        """Should invalidate follower's home feed."""
        follower_id = 1
        followed_id = 2
        mock_redis_full._storage[f"home_feed:{follower_id}:1:20"] = "data"
        
        await cache_invalidator.on_follow(follower_id, followed_id)
        
        assert f"home_feed:{follower_id}:1:20" not in mock_redis_full._storage

    @pytest.mark.asyncio
    async def test_on_follow_increments_follower_count(
        self, cache_invalidator, mock_redis_full
    ):
        """Should increment followed user's follower count."""
        follower_id = 1
        followed_id = 2
        mock_redis_full._storage[CacheKeys.user_followers_count(followed_id)] = "10"
        
        await cache_invalidator.on_follow(follower_id, followed_id)
        
        assert mock_redis_full._storage[CacheKeys.user_followers_count(followed_id)] == "11"

    @pytest.mark.asyncio
    async def test_on_follow_increments_following_count(
        self, cache_invalidator, mock_redis_full
    ):
        """Should increment follower's following count."""
        follower_id = 1
        followed_id = 2
        mock_redis_full._storage[CacheKeys.user_following_count(follower_id)] = "5"
        
        await cache_invalidator.on_follow(follower_id, followed_id)
        
        assert mock_redis_full._storage[CacheKeys.user_following_count(follower_id)] == "6"


class TestOnUnfollow:
    """Test cache updates on unfollow event."""

    @pytest.mark.asyncio
    async def test_on_unfollow_invalidates_follower_feed(
        self, cache_invalidator, mock_redis_full
    ):
        """Should invalidate follower's home feed."""
        follower_id = 1
        followed_id = 2
        mock_redis_full._storage[f"home_feed:{follower_id}:1:20"] = "data"
        
        await cache_invalidator.on_unfollow(follower_id, followed_id)
        
        assert f"home_feed:{follower_id}:1:20" not in mock_redis_full._storage

    @pytest.mark.asyncio
    async def test_on_unfollow_decrements_follower_count(
        self, cache_invalidator, mock_redis_full
    ):
        """Should decrement followed user's follower count."""
        follower_id = 1
        followed_id = 2
        mock_redis_full._storage[CacheKeys.user_followers_count(followed_id)] = "10"
        
        await cache_invalidator.on_unfollow(follower_id, followed_id)
        
        assert mock_redis_full._storage[CacheKeys.user_followers_count(followed_id)] == "9"

    @pytest.mark.asyncio
    async def test_on_unfollow_decrements_following_count(
        self, cache_invalidator, mock_redis_full
    ):
        """Should decrement follower's following count."""
        follower_id = 1
        followed_id = 2
        mock_redis_full._storage[CacheKeys.user_following_count(follower_id)] = "5"
        
        await cache_invalidator.on_unfollow(follower_id, followed_id)
        
        assert mock_redis_full._storage[CacheKeys.user_following_count(follower_id)] == "4"


class TestOnLike:
    """Test cache updates on like event."""

    @pytest.mark.asyncio
    async def test_on_like_increments_like_count(
        self, cache_invalidator, mock_redis_full
    ):
        """Should increment post like counter."""
        user_id = 1
        post_id = 100
        mock_redis_full._storage[CacheKeys.post_likes_count(post_id)] = "5"
        
        await cache_invalidator.on_like(user_id, post_id)
        
        assert mock_redis_full._storage[CacheKeys.post_likes_count(post_id)] == "6"

    @pytest.mark.asyncio
    async def test_on_like_adds_user_to_likers_set(
        self, cache_invalidator, mock_redis_full
    ):
        """Should add user to post likers set."""
        user_id = 1
        post_id = 100
        
        await cache_invalidator.on_like(user_id, post_id)
        
        assert "1" in mock_redis_full._sets[CacheKeys.post_likers(post_id)]


class TestOnUnlike:
    """Test cache updates on unlike event."""

    @pytest.mark.asyncio
    async def test_on_unlike_decrements_like_count(
        self, cache_invalidator, mock_redis_full
    ):
        """Should decrement post like counter."""
        user_id = 1
        post_id = 100
        mock_redis_full._storage[CacheKeys.post_likes_count(post_id)] = "5"
        
        await cache_invalidator.on_unlike(user_id, post_id)
        
        assert mock_redis_full._storage[CacheKeys.post_likes_count(post_id)] == "4"

    @pytest.mark.asyncio
    async def test_on_unlike_removes_user_from_likers_set(
        self, cache_invalidator, mock_redis_full
    ):
        """Should remove user from post likers set."""
        user_id = 1
        post_id = 100
        mock_redis_full._sets[CacheKeys.post_likers(post_id)] = {"1", "2", "3"}
        
        await cache_invalidator.on_unlike(user_id, post_id)
        
        assert "1" not in mock_redis_full._sets[CacheKeys.post_likers(post_id)]


class TestCacheWarming:
    """Test cache warming methods."""

    @pytest.mark.asyncio
    async def test_warm_user_cache_sets_profile_and_username(
        self, cache_invalidator, mock_redis_full
    ):
        """Should warm user profile and username lookup caches."""
        user_id = 123
        username = "testuser"
        profile_data = {"id": 123, "username": "testuser", "followers_count": 100}
        
        await cache_invalidator.warm_user_cache(user_id, profile_data, username, ttl=300)
        
        # Check profile was cached
        import json
        cached_profile = json.loads(mock_redis_full._storage[CacheKeys.user(user_id)])
        assert cached_profile == profile_data
        
        # Check username lookup was cached
        assert mock_redis_full._storage[CacheKeys.user_by_username(username)] == "123"

    @pytest.mark.asyncio
    async def test_warm_post_cache_sets_post_and_likes(
        self, cache_invalidator, mock_redis_full
    ):
        """Should warm post cache and like counter."""
        post_id = 456
        post_data = {"id": 456, "body": "Test post"}
        likes_count = 42
        
        await cache_invalidator.warm_post_cache(post_id, post_data, likes_count, ttl=60)
        
        # Check post was cached
        import json
        cached_post = json.loads(mock_redis_full._storage[CacheKeys.post(post_id)])
        assert cached_post == post_data
        
        # Check likes counter was set
        assert mock_redis_full._storage[CacheKeys.post_likes_count(post_id)] == "42"


class TestClearAllCaches:
    """Test clear all caches method."""

    @pytest.mark.asyncio
    async def test_clear_all_caches_removes_everything(
        self, cache_invalidator, mock_redis_full
    ):
        """Should clear all cached data."""
        # Add various cache entries
        mock_redis_full._storage["user:1"] = "data"
        mock_redis_full._storage["post:1"] = "data"
        mock_redis_full._sets["likers:1"] = {"a", "b"}
        mock_redis_full._lists["feed:1"] = ["x", "y"]
        
        result = await cache_invalidator.clear_all_caches()
        
        assert result is True
        assert len(mock_redis_full._storage) == 0
        assert len(mock_redis_full._sets) == 0
        assert len(mock_redis_full._lists) == 0

