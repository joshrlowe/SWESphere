"""
Core application modules.

Exports:
- Security utilities (password hashing, JWT tokens)
- Event handlers (startup/shutdown)
- Redis key management
- Pagination utilities
- WebSocket connection management
- Database monitoring
"""

from app.core.db_monitoring import (
    get_query_stats,
    log_query_stats,
    query_stats,
    query_timer,
    reset_query_stats,
    setup_pool_monitoring,
    setup_query_logging,
    timed_query,
    SLOW_QUERY_THRESHOLD_MS,
)
from app.core.pagination import (
    calculate_skip,
    calculate_pages,
    has_next_page,
    has_prev_page,
    PaginatedResult,
)
from app.core.redis_keys import redis_keys, RedisKeys, CacheKeys
from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
    decode_token,
    TokenBlacklist,
    blacklist_token,
    is_token_blacklisted,
)
from app.core.websocket import (
    ConnectionManager,
    MessageType,
    connection_manager,
    build_message,
    build_notification_message,
    build_unread_count_message,
)

__all__ = [
    # Database monitoring
    "setup_query_logging",
    "setup_pool_monitoring",
    "query_timer",
    "timed_query",
    "query_stats",
    "get_query_stats",
    "log_query_stats",
    "reset_query_stats",
    "SLOW_QUERY_THRESHOLD_MS",
    # Pagination
    "calculate_skip",
    "calculate_pages",
    "has_next_page",
    "has_prev_page",
    "PaginatedResult",
    # Redis keys
    "redis_keys",
    "RedisKeys",
    "CacheKeys",
    # Password
    "hash_password",
    "verify_password",
    "validate_password_strength",
    # JWT
    "create_access_token",
    "create_refresh_token",
    "verify_access_token",
    "verify_refresh_token",
    "decode_token",
    # Blacklist
    "TokenBlacklist",
    "blacklist_token",
    "is_token_blacklisted",
    # WebSocket
    "ConnectionManager",
    "MessageType",
    "connection_manager",
    "build_message",
    "build_notification_message",
    "build_unread_count_message",
]
