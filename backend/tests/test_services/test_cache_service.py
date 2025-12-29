"""
Tests for CacheService.

Covers:
- Basic string operations (get, set, delete)
- JSON operations
- List operations (for feeds)
- Counter operations (write-through pattern)
- Set operations (for tracking)
- Pattern-based deletion
- Error handling
"""

import json
import pytest
from unittest.mock import AsyncMock

from app.services.cache_service import CacheService, DEFAULT_TTL


class TestBasicOperations:
    """Test basic string operations."""

    @pytest.mark.asyncio
    async def test_get_returns_value_when_exists(self, cache_service, mock_redis_full):
        """Should return cached value when key exists."""
        mock_redis_full._storage["test:key"] = "test_value"
        
        result = await cache_service.get("test:key")
        
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_exists(self, cache_service):
        """Should return None when key doesn't exist."""
        result = await cache_service.get("nonexistent:key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_set_stores_value_with_ttl(self, cache_service, mock_redis_full):
        """Should store value with TTL."""
        result = await cache_service.set("test:key", "test_value", ttl=300)
        
        assert result is True
        assert mock_redis_full._storage["test:key"] == "test_value"

    @pytest.mark.asyncio
    async def test_set_uses_default_ttl(self, cache_service, mock_redis_full):
        """Should use default TTL when not specified."""
        result = await cache_service.set("test:key", "value")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_removes_key(self, cache_service, mock_redis_full):
        """Should delete existing key."""
        mock_redis_full._storage["test:key"] = "value"
        
        result = await cache_service.delete("test:key")
        
        assert result is True
        assert "test:key" not in mock_redis_full._storage

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_exists(self, cache_service):
        """Should return False when key doesn't exist."""
        result = await cache_service.delete("nonexistent:key")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_key_exists(self, cache_service, mock_redis_full):
        """Should return True when key exists."""
        mock_redis_full._storage["test:key"] = "value"
        
        result = await cache_service.exists("test:key")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_key_not_exists(self, cache_service):
        """Should return False when key doesn't exist."""
        result = await cache_service.exists("nonexistent:key")
        
        assert result is False


class TestDeletePattern:
    """Test pattern-based deletion."""

    @pytest.mark.asyncio
    async def test_delete_pattern_removes_matching_keys(self, cache_service, mock_redis_full):
        """Should delete all keys matching pattern."""
        mock_redis_full._storage["user:1:feed"] = "data1"
        mock_redis_full._storage["user:1:profile"] = "data2"
        mock_redis_full._storage["user:2:feed"] = "data3"
        
        deleted = await cache_service.delete_pattern("user:1:*")
        
        assert deleted == 2
        assert "user:1:feed" not in mock_redis_full._storage
        assert "user:1:profile" not in mock_redis_full._storage
        assert "user:2:feed" in mock_redis_full._storage

    @pytest.mark.asyncio
    async def test_delete_pattern_returns_zero_when_no_matches(self, cache_service):
        """Should return 0 when no keys match."""
        deleted = await cache_service.delete_pattern("nonexistent:*")
        
        assert deleted == 0


class TestJSONOperations:
    """Test JSON serialization/deserialization."""

    @pytest.mark.asyncio
    async def test_set_json_stores_serialized_data(self, cache_service, mock_redis_full):
        """Should serialize and store JSON data."""
        data = {"id": 1, "name": "Test", "items": [1, 2, 3]}
        
        result = await cache_service.set_json("test:json", data)
        
        assert result is True
        stored = json.loads(mock_redis_full._storage["test:json"])
        assert stored == data

    @pytest.mark.asyncio
    async def test_get_json_returns_deserialized_data(self, cache_service, mock_redis_full):
        """Should deserialize and return JSON data."""
        data = {"id": 1, "name": "Test"}
        mock_redis_full._storage["test:json"] = json.dumps(data)
        
        result = await cache_service.get_json("test:json")
        
        assert result == data

    @pytest.mark.asyncio
    async def test_get_json_returns_none_when_not_exists(self, cache_service):
        """Should return None when key doesn't exist."""
        result = await cache_service.get_json("nonexistent:key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_json_handles_invalid_json(self, cache_service, mock_redis_full):
        """Should return None for invalid JSON."""
        mock_redis_full._storage["test:invalid"] = "not valid json {"
        
        result = await cache_service.get_json("test:invalid")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_set_json_handles_list(self, cache_service, mock_redis_full):
        """Should handle list values."""
        data = [1, 2, 3, "four", {"five": 5}]
        
        result = await cache_service.set_json("test:list", data)
        
        assert result is True


class TestListOperations:
    """Test list operations for feeds."""

    @pytest.mark.asyncio
    async def test_get_list_returns_range(self, cache_service, mock_redis_full):
        """Should return list range."""
        mock_redis_full._lists["feed:1"] = ["post1", "post2", "post3", "post4"]
        
        result = await cache_service.get_list("feed:1", 0, 2)
        
        assert result == ["post1", "post2", "post3"]

    @pytest.mark.asyncio
    async def test_get_list_returns_all_with_negative_end(self, cache_service, mock_redis_full):
        """Should return all elements when end is -1."""
        mock_redis_full._lists["feed:1"] = ["post1", "post2", "post3"]
        
        result = await cache_service.get_list("feed:1", 0, -1)
        
        assert result == ["post1", "post2", "post3"]

    @pytest.mark.asyncio
    async def test_get_list_returns_empty_when_not_exists(self, cache_service):
        """Should return empty list when key doesn't exist."""
        result = await cache_service.get_list("nonexistent:list", 0, -1)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_set_list_replaces_list(self, cache_service, mock_redis_full):
        """Should replace entire list."""
        values = ["item1", "item2", "item3"]
        
        result = await cache_service.set_list("test:list", values, ttl=60)
        
        assert result is True
        assert mock_redis_full._lists["test:list"] == values

    @pytest.mark.asyncio
    async def test_set_list_deletes_when_empty(self, cache_service, mock_redis_full):
        """Should delete key when given empty list."""
        mock_redis_full._lists["test:list"] = ["old", "data"]
        
        result = await cache_service.set_list("test:list", [], ttl=60)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_prepend_to_list_adds_at_front(self, cache_service, mock_redis_full):
        """Should prepend value to list front."""
        mock_redis_full._lists["feed:1"] = ["post2", "post3"]
        
        result = await cache_service.prepend_to_list("feed:1", "post1", max_length=10)
        
        assert result == 3
        assert mock_redis_full._lists["feed:1"][0] == "post1"

    @pytest.mark.asyncio
    async def test_prepend_to_list_trims_to_max_length(self, cache_service, mock_redis_full):
        """Should trim list to max length after prepend."""
        mock_redis_full._lists["feed:1"] = ["post2", "post3", "post4"]
        
        await cache_service.prepend_to_list("feed:1", "post1", max_length=3)
        
        assert len(mock_redis_full._lists["feed:1"]) == 3

    @pytest.mark.asyncio
    async def test_get_list_length(self, cache_service, mock_redis_full):
        """Should return list length."""
        mock_redis_full._lists["test:list"] = ["a", "b", "c", "d"]
        
        result = await cache_service.get_list_length("test:list")
        
        assert result == 4


class TestCounterOperations:
    """Test counter operations (write-through pattern)."""

    @pytest.mark.asyncio
    async def test_incr_increments_by_one(self, cache_service, mock_redis_full):
        """Should increment counter by 1."""
        mock_redis_full._storage["counter:1"] = "5"
        
        result = await cache_service.incr("counter:1")
        
        assert result == 6

    @pytest.mark.asyncio
    async def test_incr_initializes_to_one(self, cache_service):
        """Should initialize to 1 when key doesn't exist."""
        result = await cache_service.incr("new:counter")
        
        assert result == 1

    @pytest.mark.asyncio
    async def test_incr_by_custom_amount(self, cache_service, mock_redis_full):
        """Should increment by custom amount."""
        mock_redis_full._storage["counter:1"] = "10"
        
        result = await cache_service.incr("counter:1", amount=5)
        
        assert result == 15

    @pytest.mark.asyncio
    async def test_decr_decrements_by_one(self, cache_service, mock_redis_full):
        """Should decrement counter by 1."""
        mock_redis_full._storage["counter:1"] = "5"
        
        result = await cache_service.decr("counter:1")
        
        assert result == 4

    @pytest.mark.asyncio
    async def test_decr_prevents_negative(self, cache_service, mock_redis_full):
        """Should not go below zero."""
        mock_redis_full._storage["counter:1"] = "0"
        
        result = await cache_service.decr("counter:1")
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_counter_returns_value(self, cache_service, mock_redis_full):
        """Should return counter value as int."""
        mock_redis_full._storage["counter:1"] = "42"
        
        result = await cache_service.get_counter("counter:1")
        
        assert result == 42

    @pytest.mark.asyncio
    async def test_get_counter_returns_none_when_not_exists(self, cache_service):
        """Should return None when counter doesn't exist."""
        result = await cache_service.get_counter("nonexistent:counter")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_set_counter(self, cache_service, mock_redis_full):
        """Should set counter value."""
        result = await cache_service.set_counter("counter:1", 100, ttl=3600)
        
        assert result is True
        assert mock_redis_full._storage["counter:1"] == "100"


class TestSetOperations:
    """Test set operations for tracking."""

    @pytest.mark.asyncio
    async def test_add_to_set_adds_values(self, cache_service, mock_redis_full):
        """Should add values to set."""
        result = await cache_service.add_to_set("likers:1", "user1", "user2", "user3")
        
        assert result == 3
        assert mock_redis_full._sets["likers:1"] == {"user1", "user2", "user3"}

    @pytest.mark.asyncio
    async def test_add_to_set_ignores_duplicates(self, cache_service, mock_redis_full):
        """Should not add duplicate values."""
        mock_redis_full._sets["likers:1"] = {"user1"}
        
        result = await cache_service.add_to_set("likers:1", "user1", "user2")
        
        assert result == 1  # Only user2 was new

    @pytest.mark.asyncio
    async def test_remove_from_set_removes_values(self, cache_service, mock_redis_full):
        """Should remove values from set."""
        mock_redis_full._sets["likers:1"] = {"user1", "user2", "user3"}
        
        result = await cache_service.remove_from_set("likers:1", "user1", "user2")
        
        assert result == 2
        assert mock_redis_full._sets["likers:1"] == {"user3"}

    @pytest.mark.asyncio
    async def test_is_in_set_returns_true_when_member(self, cache_service, mock_redis_full):
        """Should return True when value is in set."""
        mock_redis_full._sets["likers:1"] = {"user1", "user2"}
        
        result = await cache_service.is_in_set("likers:1", "user1")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_is_in_set_returns_false_when_not_member(self, cache_service, mock_redis_full):
        """Should return False when value is not in set."""
        mock_redis_full._sets["likers:1"] = {"user1"}
        
        result = await cache_service.is_in_set("likers:1", "user2")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_set_members(self, cache_service, mock_redis_full):
        """Should return all set members."""
        mock_redis_full._sets["likers:1"] = {"user1", "user2", "user3"}
        
        result = await cache_service.get_set_members("likers:1")
        
        assert result == {"user1", "user2", "user3"}


class TestHashOperations:
    """Test hash operations for structured data."""

    @pytest.mark.asyncio
    async def test_hset_and_hget(self, cache_service, mock_redis_full):
        """Should set and get hash field."""
        await cache_service.hset("user:1", "name", "John")
        
        result = await cache_service.hget("user:1", "name")
        
        assert result == "John"

    @pytest.mark.asyncio
    async def test_hmset_sets_multiple_fields(self, cache_service, mock_redis_full):
        """Should set multiple hash fields."""
        mapping = {"name": "John", "email": "john@example.com", "age": "30"}
        
        result = await cache_service.hmset("user:1", mapping)
        
        assert result is True
        assert mock_redis_full._hashes["user:1"] == mapping

    @pytest.mark.asyncio
    async def test_hgetall_returns_all_fields(self, cache_service, mock_redis_full):
        """Should return all hash fields."""
        mock_redis_full._hashes["user:1"] = {"name": "John", "email": "john@example.com"}
        
        result = await cache_service.hgetall("user:1")
        
        assert result == {"name": "John", "email": "john@example.com"}

    @pytest.mark.asyncio
    async def test_hdel_removes_fields(self, cache_service, mock_redis_full):
        """Should remove hash fields."""
        mock_redis_full._hashes["user:1"] = {"name": "John", "email": "john@example.com"}
        
        result = await cache_service.hdel("user:1", "email")
        
        assert result == 1
        assert "email" not in mock_redis_full._hashes["user:1"]

    @pytest.mark.asyncio
    async def test_hincrby_increments_field(self, cache_service, mock_redis_full):
        """Should increment hash field."""
        mock_redis_full._hashes["stats:1"] = {"views": "10"}
        
        result = await cache_service.hincrby("stats:1", "views", 5)
        
        assert result == 15


class TestUtilityMethods:
    """Test utility methods."""

    @pytest.mark.asyncio
    async def test_ping_returns_true_when_connected(self, cache_service):
        """Should return True when Redis is connected."""
        result = await cache_service.ping()
        
        assert result is True

    @pytest.mark.asyncio
    async def test_flush_all_clears_everything(self, cache_service, mock_redis_full):
        """Should clear all cached data."""
        mock_redis_full._storage["key1"] = "value1"
        mock_redis_full._sets["set1"] = {"a", "b"}
        mock_redis_full._lists["list1"] = ["x", "y"]
        
        result = await cache_service.flush_all()
        
        assert result is True
        assert len(mock_redis_full._storage) == 0
        assert len(mock_redis_full._sets) == 0
        assert len(mock_redis_full._lists) == 0


class TestErrorHandling:
    """Test error handling and fault tolerance."""

    @pytest.mark.asyncio
    async def test_get_handles_redis_error(self):
        """Should return None on Redis error."""
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=Exception("Connection error"))
        cache = CacheService(redis)
        
        result = await cache.get("key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_set_handles_redis_error(self):
        """Should return False on Redis error."""
        redis = AsyncMock()
        redis.setex = AsyncMock(side_effect=Exception("Connection error"))
        cache = CacheService(redis)
        
        result = await cache.set("key", "value")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_incr_handles_redis_error(self):
        """Should return -1 on Redis error."""
        redis = AsyncMock()
        redis.incrby = AsyncMock(side_effect=Exception("Connection error"))
        cache = CacheService(redis)
        
        result = await cache.incr("counter")
        
        assert result == -1

    @pytest.mark.asyncio
    async def test_get_json_handles_decode_error(self, cache_service, mock_redis_full):
        """Should return None on JSON decode error."""
        mock_redis_full._storage["bad:json"] = "{{invalid"
        
        result = await cache_service.get_json("bad:json")
        
        assert result is None

