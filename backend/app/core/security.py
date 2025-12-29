"""
Security utilities for authentication and authorization.

Provides:
- Password hashing with bcrypt
- JWT token creation and verification
- Token blacklisting via Redis
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from redis.asyncio import Redis

from app.config import settings
from app.core.redis_keys import redis_keys

logger = logging.getLogger(__name__)


# =============================================================================
# Password Hashing
# =============================================================================

_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hash string
    """
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored bcrypt hash
        
    Returns:
        True if password matches
    """
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password meets security requirements.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors: list[str] = []
    
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(
            f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
        )
    
    if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if settings.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if settings.PASSWORD_REQUIRE_DIGIT and not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    
    return len(errors) == 0, errors


# =============================================================================
# JWT Token Management
# =============================================================================

class TokenType:
    """Constants for token types."""
    ACCESS = "access"
    REFRESH = "refresh"


def _build_token_payload(
    subject: str | int,
    token_type: str,
    expires_at: datetime,
    additional_claims: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the JWT payload with standard claims."""
    now = datetime.now(timezone.utc)
    
    payload = {
        "sub": str(subject),
        "exp": expires_at,
        "iat": now,
        "nbf": now,
        "type": token_type,
        "iss": settings.APP_NAME,
    }
    
    if additional_claims:
        payload.update(additional_claims)
    
    return payload


def _encode_token(payload: dict[str, Any]) -> str:
    """Encode a payload into a JWT string."""
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Custom expiration time
        additional_claims: Extra claims to include
        
    Returns:
        Encoded JWT string
    """
    expires_at = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    payload = _build_token_payload(
        subject=subject,
        token_type=TokenType.ACCESS,
        expires_at=expires_at,
        additional_claims=additional_claims,
    )
    
    return _encode_token(payload)


def create_refresh_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token.
    
    Refresh tokens have longer expiration and are used to obtain new access tokens.
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT string
    """
    expires_at = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    payload = _build_token_payload(
        subject=subject,
        token_type=TokenType.REFRESH,
        expires_at=expires_at,
    )
    
    return _encode_token(payload)


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT string to decode
        
    Returns:
        Decoded payload if valid, None otherwise
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.APP_NAME,
        )
    except JWTError as e:
        logger.debug(f"Token decode error: {e}")
        return None


def _verify_token(token: str, expected_type: str) -> str | None:
    """Verify token and return subject if valid and correct type."""
    payload = decode_token(token)
    if payload is None:
        return None
    
    if payload.get("type") != expected_type:
        logger.debug(f"Token type mismatch: expected {expected_type}")
        return None
    
    return payload.get("sub")


def verify_access_token(token: str) -> str | None:
    """
    Verify an access token.
    
    Args:
        token: JWT access token
        
    Returns:
        User ID (subject) if valid, None otherwise
    """
    return _verify_token(token, TokenType.ACCESS)


def verify_refresh_token(token: str) -> str | None:
    """
    Verify a refresh token.
    
    Args:
        token: JWT refresh token
        
    Returns:
        User ID (subject) if valid, None otherwise
    """
    return _verify_token(token, TokenType.REFRESH)


def get_token_expiry(token: str) -> datetime | None:
    """
    Get the expiration time of a token.
    
    Args:
        token: JWT token
        
    Returns:
        Expiration datetime if valid, None otherwise
    """
    payload = decode_token(token)
    if payload is None:
        return None
    
    exp = payload.get("exp")
    if exp:
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    return None


# =============================================================================
# Token Blacklisting
# =============================================================================

def _hash_token(token: str) -> str:
    """Create a SHA256 hash of a token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


class TokenBlacklist:
    """
    Token blacklist manager using Redis.
    
    Used to invalidate tokens before natural expiration,
    such as during logout or password change.
    """
    
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
    
    async def add(self, token: str, expires_at: datetime | None = None) -> bool:
        """
        Add a token to the blacklist.
        
        Args:
            token: Token to blacklist
            expires_at: When the token expires (for TTL)
            
        Returns:
            True if added successfully
        """
        try:
            if expires_at is None:
                expires_at = get_token_expiry(token)
            
            if expires_at is None:
                ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
            else:
                now = datetime.now(timezone.utc)
                ttl = int((expires_at - now).total_seconds())
                if ttl <= 0:
                    return True  # Already expired
            
            token_hash = _hash_token(token)
            key = redis_keys.token_blacklist(token_hash)
            
            await self.redis.setex(key, ttl, "1")
            logger.debug(f"Token blacklisted: {token_hash[:16]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False
    
    async def is_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted.
        
        Args:
            token: Token to check
            
        Returns:
            True if blacklisted
        """
        try:
            token_hash = _hash_token(token)
            key = redis_keys.token_blacklist(token_hash)
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False  # Fail open
    
    async def remove(self, token: str) -> bool:
        """Remove a token from the blacklist."""
        try:
            token_hash = _hash_token(token)
            key = redis_keys.token_blacklist(token_hash)
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to remove token from blacklist: {e}")
            return False
    
    async def clear_all(self) -> int:
        """
        Clear all blacklisted tokens.
        
        Warning: Re-enables all previously revoked tokens!
        
        Returns:
            Number of tokens removed
        """
        try:
            pattern = redis_keys.token_blacklist_pattern()
            keys = [key async for key in self.redis.scan_iter(match=pattern)]
            
            if keys:
                await self.redis.delete(*keys)
            
            return len(keys)
        except Exception as e:
            logger.error(f"Failed to clear token blacklist: {e}")
            return 0


# Singleton instance management
_token_blacklist: TokenBlacklist | None = None


async def get_token_blacklist(redis: Redis) -> TokenBlacklist:
    """Get or create the token blacklist instance."""
    global _token_blacklist
    if _token_blacklist is None:
        _token_blacklist = TokenBlacklist(redis)
    return _token_blacklist


async def blacklist_token(token: str, redis: Redis) -> bool:
    """Convenience function to blacklist a token."""
    blacklist = await get_token_blacklist(redis)
    return await blacklist.add(token)


async def is_token_blacklisted(token: str, redis: Redis) -> bool:
    """Convenience function to check if token is blacklisted."""
    blacklist = await get_token_blacklist(redis)
    return await blacklist.is_blacklisted(token)
