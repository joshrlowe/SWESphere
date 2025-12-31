"""
Tests for recommendation-related Redis keys.

Verifies that all Redis key patterns for the recommendation system
are generated correctly and consistently.
"""

import pytest

from app.core.redis_keys import CacheKeys, RedisKeys, redis_keys


# =============================================================================
# RedisKeys Class Tests (Instance Methods)
# =============================================================================


class TestRedisKeysAffinityMethods:
    """Test RedisKeys instance methods for affinity."""

    def test_affinity_key_format(self):
        """Affinity key should follow pattern affinity:{user_id}:{author_id}."""
        key = redis_keys.affinity(user_id=123, author_id=456)
        assert key == "affinity:123:456"

    def test_affinity_key_different_users(self):
        """Different user pairs should generate different keys."""
        key1 = redis_keys.affinity(user_id=1, author_id=2)
        key2 = redis_keys.affinity(user_id=2, author_id=1)
        key3 = redis_keys.affinity(user_id=1, author_id=3)
        
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_affinity_key_self(self):
        """Self-affinity key should still be valid (even if not used)."""
        key = redis_keys.affinity(user_id=1, author_id=1)
        assert key == "affinity:1:1"

    def test_affinity_pattern_format(self):
        """Affinity pattern should match all affinities for a user."""
        pattern = redis_keys.affinity_pattern(user_id=123)
        assert pattern == "affinity:123:*"

    def test_affinity_pattern_for_scan(self):
        """Pattern should be usable with Redis SCAN."""
        pattern = redis_keys.affinity_pattern(user_id=1)
        # Pattern should end with * for glob matching
        assert pattern.endswith("*")
        assert "affinity:1:" in pattern


class TestRedisKeysRankedFeedMethods:
    """Test RedisKeys instance methods for ranked feeds."""

    def test_ranked_feed_key_format(self):
        """Ranked feed key should follow pattern ranked_feed:{user_id}."""
        key = redis_keys.ranked_feed(user_id=123)
        assert key == "ranked_feed:123"

    def test_ranked_feed_different_users(self):
        """Different users should have different feed keys."""
        key1 = redis_keys.ranked_feed(user_id=1)
        key2 = redis_keys.ranked_feed(user_id=2)
        
        assert key1 != key2
        assert key1 == "ranked_feed:1"
        assert key2 == "ranked_feed:2"

    def test_ranked_feed_pattern_format(self):
        """Ranked feed pattern should match all ranked feeds."""
        pattern = redis_keys.ranked_feed_pattern()
        assert pattern == "ranked_feed:*"


# =============================================================================
# CacheKeys Class Tests (Static Methods)
# =============================================================================


class TestCacheKeysAffinityMethods:
    """Test CacheKeys static methods for affinity."""

    def test_affinity_key_static(self):
        """Static affinity key should match instance method."""
        static_key = CacheKeys.affinity(user_id=123, author_id=456)
        instance_key = redis_keys.affinity(user_id=123, author_id=456)
        
        assert static_key == instance_key
        assert static_key == "affinity:123:456"

    def test_affinity_key_no_instance_needed(self):
        """Should be callable without instantiation."""
        # This should work without creating a CacheKeys instance
        key = CacheKeys.affinity(1, 2)
        assert key == "affinity:1:2"


class TestCacheKeysRankedFeedMethods:
    """Test CacheKeys static methods for ranked feeds."""

    def test_ranked_feed_key_static(self):
        """Static ranked feed key should match instance method."""
        static_key = CacheKeys.ranked_feed(user_id=123)
        instance_key = redis_keys.ranked_feed(user_id=123)
        
        assert static_key == instance_key
        assert static_key == "ranked_feed:123"


# =============================================================================
# Key Consistency Tests
# =============================================================================


class TestKeyConsistency:
    """Test that keys are consistent and don't conflict with existing patterns."""

    def test_affinity_prefix_unique(self):
        """Affinity prefix should not conflict with other prefixes."""
        affinity_key = redis_keys.affinity(1, 2)
        
        # Should not start with other common prefixes
        assert not affinity_key.startswith("user:")
        assert not affinity_key.startswith("post:")
        assert not affinity_key.startswith("cache:")
        assert not affinity_key.startswith("home_feed:")

    def test_ranked_feed_prefix_unique(self):
        """Ranked feed prefix should not conflict with home_feed."""
        ranked_key = redis_keys.ranked_feed(1)
        home_key = redis_keys.home_feed(1, 1, 20)
        
        assert not ranked_key.startswith("home_feed:")
        assert not home_key.startswith("ranked_feed:")

    def test_key_types_are_strings(self):
        """All keys should be strings."""
        assert isinstance(redis_keys.affinity(1, 2), str)
        assert isinstance(redis_keys.affinity_pattern(1), str)
        assert isinstance(redis_keys.ranked_feed(1), str)
        assert isinstance(redis_keys.ranked_feed_pattern(), str)

    def test_keys_dont_contain_special_chars(self):
        """Keys should not contain characters that could cause issues."""
        keys = [
            redis_keys.affinity(1, 2),
            redis_keys.ranked_feed(1),
        ]
        
        for key in keys:
            # Should only contain alphanumeric, colons, and underscores
            assert all(c.isalnum() or c in ":_" for c in key)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestKeyEdgeCases:
    """Test edge cases in key generation."""

    def test_affinity_large_user_ids(self):
        """Should handle large user IDs."""
        key = redis_keys.affinity(user_id=9999999999, author_id=8888888888)
        assert key == "affinity:9999999999:8888888888"

    def test_affinity_zero_user_id(self):
        """Should handle zero as user ID (though unlikely in practice)."""
        key = redis_keys.affinity(user_id=0, author_id=1)
        assert key == "affinity:0:1"

    def test_ranked_feed_large_user_id(self):
        """Should handle large user IDs for ranked feeds."""
        key = redis_keys.ranked_feed(user_id=9999999999)
        assert key == "ranked_feed:9999999999"


# =============================================================================
# Prefix Constants Tests
# =============================================================================


class TestPrefixConstants:
    """Test that prefix constants are properly defined."""

    def test_affinity_prefix_defined(self):
        """AFFINITY_PREFIX should be defined in RedisKeys."""
        keys = RedisKeys()
        assert hasattr(keys, "AFFINITY_PREFIX")
        assert keys.AFFINITY_PREFIX == "affinity"

    def test_ranked_feed_prefix_defined(self):
        """RANKED_FEED_PREFIX should be defined in RedisKeys."""
        keys = RedisKeys()
        assert hasattr(keys, "RANKED_FEED_PREFIX")
        assert keys.RANKED_FEED_PREFIX == "ranked_feed"

    def test_prefixes_used_in_keys(self):
        """Keys should use the defined prefixes."""
        keys = RedisKeys()
        
        affinity_key = keys.affinity(1, 2)
        assert affinity_key.startswith(keys.AFFINITY_PREFIX + ":")
        
        ranked_key = keys.ranked_feed(1)
        assert ranked_key.startswith(keys.RANKED_FEED_PREFIX + ":")

