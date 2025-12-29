"""
Core application modules.

Exports:
- Security utilities (password hashing, JWT tokens)
- Event handlers (startup/shutdown)
- Redis key management
"""

from app.core.redis_keys import redis_keys, RedisKeys
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

__all__ = [
    # Redis keys
    "redis_keys",
    "RedisKeys",
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
]
