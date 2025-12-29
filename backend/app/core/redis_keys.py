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
    EMAIL_VERIFY_PREFIX = "email_verify"
    PASSWORD_RESET_PREFIX = "password_reset"
    NOTIFICATION_CHANNEL_PREFIX = "notifications"
    NOTIFICATION_COUNT_PREFIX = "notification_count"
    RATE_LIMIT_PREFIX = "rate_limit"
    CACHE_PREFIX = "cache"
    HOME_FEED_PREFIX = "home_feed"
    EXPLORE_FEED_PREFIX = "explore_feed"

    # =========================================================================
    # Authentication Keys
    # =========================================================================

    def refresh_token(self, user_id: int) -> str:
        """Generate key for storing user's refresh token."""
        return f"{self.REFRESH_TOKEN_PREFIX}:{user_id}"

    def token_blacklist(self, token_hash: str) -> str:
        """Generate key for blacklisted token entry."""
        return f"{self.TOKEN_BLACKLIST_PREFIX}:{token_hash}"

    def token_blacklist_pattern(self) -> str:
        """Pattern for scanning all blacklisted tokens."""
        return f"{self.TOKEN_BLACKLIST_PREFIX}:*"

    def email_verify_token(self, token: str) -> str:
        """Generate key for email verification token."""
        return f"{self.EMAIL_VERIFY_PREFIX}:{token}"

    def password_reset_token(self, token: str) -> str:
        """Generate key for password reset token."""
        return f"{self.PASSWORD_RESET_PREFIX}:{token}"

    # =========================================================================
    # Notification Keys
    # =========================================================================

    def notification_channel(self, user_id: int) -> str:
        """Generate Redis pub/sub channel for user notifications."""
        return f"{self.NOTIFICATION_CHANNEL_PREFIX}:{user_id}"

    def notification_count(self, user_id: int) -> str:
        """Generate key for cached unread notification count."""
        return f"{self.NOTIFICATION_COUNT_PREFIX}:{user_id}"

    # =========================================================================
    # Feed Cache Keys
    # =========================================================================

    def home_feed(self, user_id: int, page: int, per_page: int) -> str:
        """Generate key for cached home feed page."""
        return f"{self.HOME_FEED_PREFIX}:{user_id}:{page}:{per_page}"

    def home_feed_pattern(self, user_id: int) -> str:
        """Pattern for scanning all home feed cache for a user."""
        return f"{self.HOME_FEED_PREFIX}:{user_id}:*"

    def explore_feed(self, page: int, per_page: int) -> str:
        """Generate key for cached explore feed page."""
        return f"{self.EXPLORE_FEED_PREFIX}:{page}:{per_page}"

    def explore_feed_pattern(self) -> str:
        """Pattern for scanning all explore feed cache."""
        return f"{self.EXPLORE_FEED_PREFIX}:*"

    # =========================================================================
    # Rate Limiting Keys
    # =========================================================================

    def rate_limit(self, identifier: str, endpoint: str) -> str:
        """Generate key for rate limiting."""
        return f"{self.RATE_LIMIT_PREFIX}:{endpoint}:{identifier}"

    def rate_limit_pattern(self, endpoint: str) -> str:
        """Pattern for scanning rate limit keys for an endpoint."""
        return f"{self.RATE_LIMIT_PREFIX}:{endpoint}:*"

    # =========================================================================
    # Generic Cache Keys
    # =========================================================================

    def cache(self, namespace: str, key: str) -> str:
        """Generate generic cache key."""
        return f"{self.CACHE_PREFIX}:{namespace}:{key}"

    def cache_pattern(self, namespace: str) -> str:
        """Pattern for scanning cache keys in a namespace."""
        return f"{self.CACHE_PREFIX}:{namespace}:*"

    # =========================================================================
    # User-Specific Keys
    # =========================================================================

    def user_session(self, user_id: int, session_id: str) -> str:
        """Generate key for user session tracking."""
        return f"session:{user_id}:{session_id}"

    def user_sessions_pattern(self, user_id: int) -> str:
        """Pattern for scanning all sessions for a user."""
        return f"session:{user_id}:*"


# Singleton instance for convenience
redis_keys = RedisKeys()
