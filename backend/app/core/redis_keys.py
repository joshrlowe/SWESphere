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
        key = keys.user(user_id=123)  # "user:123"
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

    # Entity prefixes
    USER_PREFIX = "user"
    USER_BY_USERNAME_PREFIX = "user_by_username"
    POST_PREFIX = "post"
    POST_LIKES_PREFIX = "post_likes"
    USER_FOLLOWERS_PREFIX = "user_followers"
    USER_FOLLOWING_PREFIX = "user_following"

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

    # =========================================================================
    # Entity Cache Keys
    # =========================================================================

    def user(self, user_id: int) -> str:
        """Generate key for cached user profile."""
        return f"{self.USER_PREFIX}:{user_id}"

    def user_pattern(self) -> str:
        """Pattern for scanning all cached user profiles."""
        return f"{self.USER_PREFIX}:*"

    def user_by_username(self, username: str) -> str:
        """Generate key for username-to-user-id mapping."""
        return f"{self.USER_BY_USERNAME_PREFIX}:{username.lower()}"

    def user_by_username_pattern(self) -> str:
        """Pattern for scanning all username mappings."""
        return f"{self.USER_BY_USERNAME_PREFIX}:*"

    def post(self, post_id: int) -> str:
        """Generate key for cached post."""
        return f"{self.POST_PREFIX}:{post_id}"

    def post_pattern(self) -> str:
        """Pattern for scanning all cached posts."""
        return f"{self.POST_PREFIX}:*"

    # =========================================================================
    # Counter Keys
    # =========================================================================

    def post_likes_count(self, post_id: int) -> str:
        """Generate key for post likes counter."""
        return f"{self.POST_LIKES_PREFIX}:{post_id}:count"

    def post_likers(self, post_id: int) -> str:
        """Generate key for set of user IDs who liked a post."""
        return f"{self.POST_LIKES_PREFIX}:{post_id}:users"

    def user_followers_count(self, user_id: int) -> str:
        """Generate key for user's followers count."""
        return f"{self.USER_FOLLOWERS_PREFIX}:{user_id}:count"

    def user_following_count(self, user_id: int) -> str:
        """Generate key for user's following count."""
        return f"{self.USER_FOLLOWING_PREFIX}:{user_id}:count"

    def notifications_unread(self, user_id: int) -> str:
        """Generate key for unread notifications count (alias for notification_count)."""
        return self.notification_count(user_id)

    # =========================================================================
    # Token Blacklist
    # =========================================================================

    def token_blacklist_jti(self, jti: str) -> str:
        """Generate key for blacklisted token by JTI."""
        return f"{self.TOKEN_BLACKLIST_PREFIX}:jti:{jti}"


# =============================================================================
# Static Key Builders (for convenience)
# =============================================================================


class CacheKeys:
    """
    Static cache key builders for common patterns.

    Provides a simpler interface than RedisKeys for common use cases.
    All methods are static and can be called without instantiation.
    """

    @staticmethod
    def user(user_id: int) -> str:
        """Generate key for cached user profile."""
        return f"user:{user_id}"

    @staticmethod
    def user_by_username(username: str) -> str:
        """Generate key for username-to-user-id lookup."""
        return f"user_by_username:{username.lower()}"

    @staticmethod
    def home_feed(user_id: int) -> str:
        """Generate key for user's home feed cache."""
        return f"home_feed:{user_id}"

    @staticmethod
    def home_feed_page(user_id: int, page: int, per_page: int) -> str:
        """Generate key for specific page of home feed."""
        return f"home_feed:{user_id}:{page}:{per_page}"

    @staticmethod
    def explore_feed() -> str:
        """Generate key for explore feed cache."""
        return "explore_feed"

    @staticmethod
    def explore_feed_page(page: int, per_page: int) -> str:
        """Generate key for specific page of explore feed."""
        return f"explore_feed:{page}:{per_page}"

    @staticmethod
    def post(post_id: int) -> str:
        """Generate key for cached post."""
        return f"post:{post_id}"

    @staticmethod
    def post_likes_count(post_id: int) -> str:
        """Generate key for post likes counter."""
        return f"post_likes:{post_id}:count"

    @staticmethod
    def post_likers(post_id: int) -> str:
        """Generate key for set of user IDs who liked a post."""
        return f"post_likes:{post_id}:users"

    @staticmethod
    def notifications_unread(user_id: int) -> str:
        """Generate key for unread notifications count."""
        return f"notification_count:{user_id}"

    @staticmethod
    def user_followers_count(user_id: int) -> str:
        """Generate key for user's followers count."""
        return f"user_followers:{user_id}:count"

    @staticmethod
    def user_following_count(user_id: int) -> str:
        """Generate key for user's following count."""
        return f"user_following:{user_id}:count"

    @staticmethod
    def token_blacklist(jti: str) -> str:
        """Generate key for blacklisted token by JTI."""
        return f"token_blacklist:jti:{jti}"

    # =========================================================================
    # Pattern Builders (for invalidation)
    # =========================================================================

    @staticmethod
    def user_pattern(user_id: int) -> str:
        """Pattern for all user-related cache keys."""
        return f"user:{user_id}*"

    @staticmethod
    def home_feed_pattern(user_id: int) -> str:
        """Pattern for all home feed pages for a user."""
        return f"home_feed:{user_id}:*"

    @staticmethod
    def explore_feed_pattern() -> str:
        """Pattern for all explore feed pages."""
        return "explore_feed:*"

    @staticmethod
    def post_pattern(post_id: int) -> str:
        """Pattern for all post-related cache keys."""
        return f"post:{post_id}*"


# Singleton instance for convenience
redis_keys = RedisKeys()
