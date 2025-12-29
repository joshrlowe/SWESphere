"""
Redis caching service.

Provides a clean abstraction over Redis operations for:
- Basic string operations
- JSON serialization/deserialization
- List operations (for feeds)
- Counter operations (write-through pattern)
- Pattern-based invalidation

All operations are fault-tolerant and log errors without raising.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# Constants
# =============================================================================

# Default TTL values (in seconds)
DEFAULT_TTL = 300  # 5 minutes
FEED_TTL = 60  # 1 minute
PROFILE_TTL = 300  # 5 minutes
COUNTER_TTL = 3600  # 1 hour


# =============================================================================
# Cache Service
# =============================================================================


class CacheService:
    """
    Redis caching service with typed operations.

    Provides:
    - Basic string get/set/delete
    - JSON serialization with automatic encoding
    - List operations for feed caching
    - Atomic counter operations for write-through caching
    - Pattern-based cache invalidation

    All operations are fault-tolerant: failures are logged but don't raise.
    """

    def __init__(self, redis: "Redis") -> None:
        """
        Initialize cache service.

        Args:
            redis: Async Redis client with decode_responses=True
        """
        self._redis = redis

    # =========================================================================
    # Basic String Operations
    # =========================================================================

    async def get(self, key: str) -> str | None:
        """
        Get a string value from cache.

        Args:
            key: Cache key

        Returns:
            Cached string or None if not found/error
        """
        try:
            return await self._redis.get(key)
        except Exception as e:
            logger.warning(f"Cache GET error for key '{key}': {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: int = DEFAULT_TTL,
    ) -> bool:
        """
        Set a string value in cache.

        Args:
            key: Cache key
            value: String value to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            await self._redis.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning(f"Cache SET error for key '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False otherwise
        """
        try:
            result = await self._redis.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache DELETE error for key '{key}': {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Uses SCAN for safety (non-blocking).

        Args:
            pattern: Redis glob pattern (e.g., "user:*:feed")

        Returns:
            Number of keys deleted
        """
        try:
            deleted = 0
            async for key in self._redis.scan_iter(match=pattern, count=100):
                await self._redis.delete(key)
                deleted += 1
            return deleted
        except Exception as e:
            logger.warning(f"Cache DELETE PATTERN error for '{pattern}': {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            return await self._redis.exists(key) > 0
        except Exception as e:
            logger.warning(f"Cache EXISTS error for key '{key}': {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set TTL on an existing key.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            True if TTL was set, False otherwise
        """
        try:
            return await self._redis.expire(key, ttl)
        except Exception as e:
            logger.warning(f"Cache EXPIRE error for key '{key}': {e}")
            return False

    # =========================================================================
    # JSON Operations
    # =========================================================================

    async def get_json(self, key: str) -> dict[str, Any] | list | None:
        """
        Get and deserialize a JSON value.

        Args:
            key: Cache key

        Returns:
            Deserialized dict/list or None if not found/error
        """
        try:
            data = await self._redis.get(key)
            if data is None:
                return None
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.warning(f"Cache JSON decode error for key '{key}': {e}")
            return None
        except Exception as e:
            logger.warning(f"Cache GET JSON error for key '{key}': {e}")
            return None

    async def set_json(
        self,
        key: str,
        value: dict[str, Any] | list,
        ttl: int = DEFAULT_TTL,
    ) -> bool:
        """
        Serialize and cache a JSON value.

        Args:
            key: Cache key
            value: Dict or list to serialize and cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            serialized = json.dumps(value, default=str)
            await self._redis.setex(key, ttl, serialized)
            return True
        except (TypeError, ValueError) as e:
            logger.warning(f"Cache JSON encode error for key '{key}': {e}")
            return False
        except Exception as e:
            logger.warning(f"Cache SET JSON error for key '{key}': {e}")
            return False

    # =========================================================================
    # List Operations (for Feeds)
    # =========================================================================

    async def get_list(
        self,
        key: str,
        start: int = 0,
        end: int = -1,
    ) -> list[str]:
        """
        Get a range of elements from a list.

        Args:
            key: Cache key
            start: Start index (0-based)
            end: End index (inclusive, -1 for all)

        Returns:
            List of string elements
        """
        try:
            return await self._redis.lrange(key, start, end)
        except Exception as e:
            logger.warning(f"Cache LRANGE error for key '{key}': {e}")
            return []

    async def set_list(
        self,
        key: str,
        values: list[str],
        ttl: int = DEFAULT_TTL,
    ) -> bool:
        """
        Replace a list with new values.

        Uses a transaction to ensure atomicity.

        Args:
            key: Cache key
            values: List of string values
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        if not values:
            return await self.delete(key)

        try:
            async with self._redis.pipeline() as pipe:
                await pipe.delete(key)
                await pipe.rpush(key, *values)
                await pipe.expire(key, ttl)
                await pipe.execute()
            return True
        except Exception as e:
            logger.warning(f"Cache SET LIST error for key '{key}': {e}")
            return False

    async def prepend_to_list(
        self,
        key: str,
        value: str,
        max_length: int = 100,
    ) -> int:
        """
        Prepend a value to a list and trim to max length.

        Used for maintaining feed caches with new posts.

        Args:
            key: Cache key
            value: Value to prepend
            max_length: Maximum list length after operation

        Returns:
            New list length, or -1 on error
        """
        try:
            async with self._redis.pipeline() as pipe:
                await pipe.lpush(key, value)
                await pipe.ltrim(key, 0, max_length - 1)
                results = await pipe.execute()
            return results[0]  # lpush returns new length
        except Exception as e:
            logger.warning(f"Cache PREPEND error for key '{key}': {e}")
            return -1

    async def append_to_list(
        self,
        key: str,
        value: str,
        max_length: int = 100,
    ) -> int:
        """
        Append a value to a list and trim to max length.

        Args:
            key: Cache key
            value: Value to append
            max_length: Maximum list length after operation

        Returns:
            New list length, or -1 on error
        """
        try:
            async with self._redis.pipeline() as pipe:
                await pipe.rpush(key, value)
                await pipe.ltrim(key, -max_length, -1)
                results = await pipe.execute()
            return results[0]
        except Exception as e:
            logger.warning(f"Cache APPEND error for key '{key}': {e}")
            return -1

    async def get_list_length(self, key: str) -> int:
        """
        Get the length of a list.

        Args:
            key: Cache key

        Returns:
            List length, or 0 on error
        """
        try:
            return await self._redis.llen(key)
        except Exception as e:
            logger.warning(f"Cache LLEN error for key '{key}': {e}")
            return 0

    # =========================================================================
    # Counter Operations (Write-Through Pattern)
    # =========================================================================

    async def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment a counter.

        Args:
            key: Counter key
            amount: Amount to increment (default 1)

        Returns:
            New counter value, or -1 on error
        """
        try:
            return await self._redis.incrby(key, amount)
        except Exception as e:
            logger.warning(f"Cache INCR error for key '{key}': {e}")
            return -1

    async def decr(self, key: str, amount: int = 1) -> int:
        """
        Decrement a counter (ensures non-negative).

        Args:
            key: Counter key
            amount: Amount to decrement (default 1)

        Returns:
            New counter value, or -1 on error
        """
        try:
            # Get current value first to prevent going negative
            current = await self._redis.get(key)
            if current is not None and int(current) <= 0:
                return 0

            result = await self._redis.decrby(key, amount)
            # Ensure non-negative
            if result < 0:
                await self._redis.set(key, "0")
                return 0
            return result
        except Exception as e:
            logger.warning(f"Cache DECR error for key '{key}': {e}")
            return -1

    async def get_counter(self, key: str) -> int | None:
        """
        Get a counter value.

        Args:
            key: Counter key

        Returns:
            Counter value, or None if not found/error
        """
        try:
            value = await self._redis.get(key)
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None
        except Exception as e:
            logger.warning(f"Cache GET COUNTER error for key '{key}': {e}")
            return None

    async def set_counter(
        self,
        key: str,
        value: int,
        ttl: int = COUNTER_TTL,
    ) -> bool:
        """
        Set a counter value.

        Args:
            key: Counter key
            value: Counter value
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            await self._redis.setex(key, ttl, str(value))
            return True
        except Exception as e:
            logger.warning(f"Cache SET COUNTER error for key '{key}': {e}")
            return False

    # =========================================================================
    # Set Operations (for tracking)
    # =========================================================================

    async def add_to_set(self, key: str, *values: str) -> int:
        """
        Add values to a set.

        Args:
            key: Set key
            values: Values to add

        Returns:
            Number of new elements added
        """
        if not values:
            return 0
        try:
            return await self._redis.sadd(key, *values)
        except Exception as e:
            logger.warning(f"Cache SADD error for key '{key}': {e}")
            return 0

    async def remove_from_set(self, key: str, *values: str) -> int:
        """
        Remove values from a set.

        Args:
            key: Set key
            values: Values to remove

        Returns:
            Number of elements removed
        """
        if not values:
            return 0
        try:
            return await self._redis.srem(key, *values)
        except Exception as e:
            logger.warning(f"Cache SREM error for key '{key}': {e}")
            return 0

    async def is_in_set(self, key: str, value: str) -> bool:
        """
        Check if a value is in a set.

        Args:
            key: Set key
            value: Value to check

        Returns:
            True if value is in set
        """
        try:
            return await self._redis.sismember(key, value)
        except Exception as e:
            logger.warning(f"Cache SISMEMBER error for key '{key}': {e}")
            return False

    async def get_set_members(self, key: str) -> set[str]:
        """
        Get all members of a set.

        Args:
            key: Set key

        Returns:
            Set of string members
        """
        try:
            return await self._redis.smembers(key)
        except Exception as e:
            logger.warning(f"Cache SMEMBERS error for key '{key}': {e}")
            return set()

    # =========================================================================
    # Hash Operations (for structured data)
    # =========================================================================

    async def hget(self, key: str, field: str) -> str | None:
        """Get a hash field value."""
        try:
            return await self._redis.hget(key, field)
        except Exception as e:
            logger.warning(f"Cache HGET error for key '{key}': {e}")
            return None

    async def hset(self, key: str, field: str, value: str) -> bool:
        """Set a hash field value."""
        try:
            await self._redis.hset(key, field, value)
            return True
        except Exception as e:
            logger.warning(f"Cache HSET error for key '{key}': {e}")
            return False

    async def hgetall(self, key: str) -> dict[str, str]:
        """Get all hash fields and values."""
        try:
            return await self._redis.hgetall(key)
        except Exception as e:
            logger.warning(f"Cache HGETALL error for key '{key}': {e}")
            return {}

    async def hmset(
        self,
        key: str,
        mapping: dict[str, str],
        ttl: int | None = None,
    ) -> bool:
        """Set multiple hash fields."""
        if not mapping:
            return False
        try:
            await self._redis.hset(key, mapping=mapping)
            if ttl:
                await self._redis.expire(key, ttl)
            return True
        except Exception as e:
            logger.warning(f"Cache HMSET error for key '{key}': {e}")
            return False

    async def hdel(self, key: str, *fields: str) -> int:
        """Delete hash fields."""
        if not fields:
            return 0
        try:
            return await self._redis.hdel(key, *fields)
        except Exception as e:
            logger.warning(f"Cache HDEL error for key '{key}': {e}")
            return 0

    async def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        """Increment a hash field by amount."""
        try:
            return await self._redis.hincrby(key, field, amount)
        except Exception as e:
            logger.warning(f"Cache HINCRBY error for key '{key}': {e}")
            return -1

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            return await self._redis.ping()
        except Exception:
            return False

    async def flush_all(self) -> bool:
        """
        Flush all keys (USE WITH CAUTION).

        Only for testing/development.
        """
        try:
            await self._redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Cache FLUSHDB error: {e}")
            return False

