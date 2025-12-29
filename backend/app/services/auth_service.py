"""
Authentication service.

Handles user registration, login, token management, password reset,
and email verification.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.config import settings
from app.core.redis_keys import redis_keys
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    validate_password_strength,
    verify_password,
    verify_refresh_token,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginResponse, TokenResponse
from app.schemas.user import UserCreate, UserResponse

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service for authentication operations.

    Handles:
    - User registration with email uniqueness validation
    - Login with lockout protection
    - Token refresh with rotation
    - Logout with token revocation
    - Email verification
    - Password reset flow
    """

    # Token TTLs
    EMAIL_VERIFY_TOKEN_TTL = 24 * 60 * 60  # 24 hours
    PASSWORD_RESET_TOKEN_TTL = 60 * 60  # 1 hour

    def __init__(self, user_repo: UserRepository, redis: Redis) -> None:
        self.user_repo = user_repo
        self.redis = redis

    # =========================================================================
    # Registration
    # =========================================================================

    async def register(self, user_data: UserCreate) -> User:
        """
        Register a new user account.

        Args:
            user_data: Registration data with email, username, password

        Returns:
            Newly created User

        Raises:
            HTTPException: If email/username exists or password too weak
        """
        # Validate password strength
        is_valid, errors = validate_password_strength(user_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"password": errors},
            )

        # Check for existing user
        existing = await self.user_repo.get_by_email_or_username(
            user_data.email, user_data.username
        )

        if existing:
            detail = (
                "Email already registered"
                if existing.email.lower() == user_data.email.lower()
                else "Username already taken"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )

        # Create user
        user = await self.user_repo.create(
            email=user_data.email,
            username=user_data.username,
            password_hash=hash_password(user_data.password),
        )

        # Queue verification email (fire and forget)
        await self._queue_verification_email(user)

        logger.info(f"New user registered: {user.username} ({user.email})")
        return user

    async def _queue_verification_email(self, user: User) -> None:
        """Generate verification token and queue email task."""
        token = secrets.token_urlsafe(32)

        # Store token -> user_id mapping
        await self.redis.setex(
            redis_keys.email_verify_token(token),
            self.EMAIL_VERIFY_TOKEN_TTL,
            str(user.id),
        )

        # TODO: Queue Celery task to send verification email
        # from app.workers.tasks.email import send_verification_email
        # send_verification_email.delay(user.email, user.username, token)
        logger.debug(f"Verification token generated for user {user.id}")

    # =========================================================================
    # Login & Logout
    # =========================================================================

    async def login(self, username_or_email: str, password: str) -> LoginResponse:
        """
        Authenticate user and return tokens.

        Args:
            username_or_email: Username or email address
            password: Plain text password

        Returns:
            LoginResponse with user info and tokens

        Raises:
            HTTPException: If credentials invalid or account locked
        """
        # Try to find user by username or email
        user = await self.user_repo.get_by_username(username_or_email)
        if not user:
            user = await self.user_repo.get_by_email(username_or_email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # Check if account is locked
        if user.is_locked:
            remaining = self._get_lockout_remaining(user)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is temporarily locked. Try again in {remaining} minutes.",
            )

        # Check if account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been deactivated",
            )

        # Verify password
        if not verify_password(password, user.password_hash):
            await self._handle_failed_login(user)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # Successful login
        await self._handle_successful_login(user)
        tokens = self._create_tokens(user.id)
        await self._store_refresh_token(user.id, tokens.refresh_token)

        logger.info(f"User logged in: {user.username}")
        return LoginResponse(
            user=UserResponse.model_validate(user),
            tokens=tokens,
        )

    async def _handle_failed_login(self, user: User) -> None:
        """Record failed login attempt and potentially lock account."""
        user.failed_login_attempts += 1

        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.LOCKOUT_DURATION_MINUTES
            )
            logger.warning(f"Account locked due to failed attempts: {user.username}")

    async def _handle_successful_login(self, user: User) -> None:
        """Reset login attempts and record login time."""
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc)

    def _get_lockout_remaining(self, user: User) -> int:
        """Get remaining lockout time in minutes."""
        if not user.locked_until:
            return 0
        remaining = user.locked_until - datetime.now(timezone.utc)
        return max(0, int(remaining.total_seconds() / 60))

    async def logout(self, user_id: int, access_token: str | None = None) -> None:
        """
        Logout user by revoking their refresh token.

        Args:
            user_id: ID of user to logout
            access_token: Optional access token to blacklist
        """
        # Delete stored refresh token
        await self.redis.delete(redis_keys.refresh_token(user_id))

        # Optionally blacklist access token
        if access_token:
            # TODO: Add to token blacklist
            pass

        logger.info(f"User logged out: {user_id}")

    # =========================================================================
    # Token Management
    # =========================================================================

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """
        Exchange refresh token for new access token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New TokenResponse with fresh tokens

        Raises:
            HTTPException: If refresh token invalid or revoked
        """
        user_id = verify_refresh_token(refresh_token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Verify token matches stored token (prevents reuse after refresh)
        stored_token = await self.redis.get(redis_keys.refresh_token(int(user_id)))
        if stored_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        # Handle bytes vs str comparison
        stored_str = (
            stored_token.decode() if isinstance(stored_token, bytes) else stored_token
        )
        if stored_str != refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
            )

        # Verify user still exists and is active
        user = await self.user_repo.get_by_id(int(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Issue new tokens (rotate refresh token for security)
        tokens = self._create_tokens(int(user_id))
        await self._store_refresh_token(int(user_id), tokens.refresh_token)

        return tokens

    async def _store_refresh_token(self, user_id: int, token: str) -> None:
        """Store refresh token in Redis with expiration."""
        ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        await self.redis.set(
            redis_keys.refresh_token(user_id),
            token,
            ex=ttl_seconds,
        )

    def _create_tokens(self, user_id: int) -> TokenResponse:
        """Generate new access and refresh token pair."""
        access_token = create_access_token(
            subject=user_id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_refresh_token(
            subject=user_id,
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # =========================================================================
    # Email Verification
    # =========================================================================

    async def verify_email(self, token: str) -> User:
        """
        Verify user's email address.

        Args:
            token: Verification token from email

        Returns:
            Updated User with verified email

        Raises:
            HTTPException: If token invalid or expired
        """
        # Look up token
        user_id = await self.redis.get(redis_keys.email_verify_token(token))
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        # Decode bytes if needed
        user_id_str = user_id.decode() if isinstance(user_id, bytes) else user_id

        # Update user
        user = await self.user_repo.get_by_id(int(user_id_str))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.email_verified:
            # Already verified, just delete token and return
            await self.redis.delete(redis_keys.email_verify_token(token))
            return user

        # Mark email as verified
        user = await self.user_repo.update(user.id, email_verified=True)

        # Delete used token
        await self.redis.delete(redis_keys.email_verify_token(token))

        logger.info(f"Email verified for user: {user.username}")
        return user  # type: ignore[return-value]

    async def resend_verification_email(self, user_id: int) -> None:
        """Resend verification email to user."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified",
            )

        await self._queue_verification_email(user)

    # =========================================================================
    # Password Reset
    # =========================================================================

    async def request_password_reset(self, email: str) -> None:
        """
        Request password reset for an account.

        Always returns success (don't reveal if email exists).

        Args:
            email: Email address to send reset link to
        """
        user = await self.user_repo.get_by_email(email)

        if user and user.is_active:
            # Generate reset token
            token = secrets.token_urlsafe(32)

            # Store token -> user_id mapping
            await self.redis.setex(
                redis_keys.password_reset_token(token),
                self.PASSWORD_RESET_TOKEN_TTL,
                str(user.id),
            )

            # TODO: Queue Celery task to send reset email
            # from app.workers.tasks.email import send_password_reset_email
            # send_password_reset_email.delay(user.email, user.username, token)
            logger.info(f"Password reset requested for: {email}")
        else:
            # Log but don't reveal to caller
            logger.debug(f"Password reset for non-existent/inactive: {email}")

    async def reset_password(self, token: str, new_password: str) -> User:
        """
        Reset user's password using reset token.

        Args:
            token: Password reset token from email
            new_password: New password to set

        Returns:
            Updated User

        Raises:
            HTTPException: If token invalid/expired or password too weak
        """
        # Validate new password
        is_valid, errors = validate_password_strength(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"password": errors},
            )

        # Look up token
        user_id = await self.redis.get(redis_keys.password_reset_token(token))
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Decode bytes if needed
        user_id_str = user_id.decode() if isinstance(user_id, bytes) else user_id

        # Update password
        user = await self.user_repo.update(
            int(user_id_str),
            password_hash=hash_password(new_password),
            failed_login_attempts=0,
            locked_until=None,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Delete used token
        await self.redis.delete(redis_keys.password_reset_token(token))

        # Revoke all refresh tokens (force re-login)
        await self.redis.delete(redis_keys.refresh_token(user.id))

        logger.info(f"Password reset completed for user: {user.username}")
        return user
