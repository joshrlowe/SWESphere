"""
Redis key management - centralized key patterns for consistency.

All Redis keys should be generated through this module to ensure
consistent naming conventions and easy auditing of Redis usage.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RedisKeys:
    """
    Redis key generator with consistent naming patterns.
    
    Usage:
        keys = RedisKeys()
        key = keys.refresh_token(user_id=123)  # "refresh_token:123"
    """
    
    # Key prefixes
    REFRESH_TOKEN_PREFIX = "refresh_token"
    TOKEN_BLACKLIST_PREFIX = "token_blacklist"
    NOTIFICATION_CHANNEL_PREFIX = "notifications"
    RATE_LIMIT_PREFIX = "rate_limit"
    CACHE_PREFIX = "cache"
    
    def refresh_token(self, user_id: int) -> str:
        """Generate key for storing user's refresh token."""
        return f"{self.REFRESH_TOKEN_PREFIX}:{user_id}"
    
    def token_blacklist(self, token_hash: str) -> str:
        """Generate key for blacklisted token entry."""
        return f"{self.TOKEN_BLACKLIST_PREFIX}:{token_hash}"
    
    def token_blacklist_pattern(self) -> str:
        """Pattern for scanning all blacklisted tokens."""
        return f"{self.TOKEN_BLACKLIST_PREFIX}:*"
    
    def notification_channel(self, user_id: int) -> str:
        """Generate Redis pub/sub channel for user notifications."""
        return f"{self.NOTIFICATION_CHANNEL_PREFIX}:{user_id}"
    
    def rate_limit(self, identifier: str, endpoint: str) -> str:
        """Generate key for rate limiting."""
        return f"{self.RATE_LIMIT_PREFIX}:{endpoint}:{identifier}"
    
    def cache(self, namespace: str, key: str) -> str:
        """Generate generic cache key."""
        return f"{self.CACHE_PREFIX}:{namespace}:{key}"


# Singleton instance for convenience
redis_keys = RedisKeys()

