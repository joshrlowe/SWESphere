"""
Authentication service.

Handles user registration, login, token management, and logout.
"""

from datetime import timedelta

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.config import settings
from app.core.redis_keys import redis_keys
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginResponse, TokenResponse
from app.schemas.user import UserCreate, UserResponse


class AuthService:
    """Service for authentication operations."""

    def __init__(self, user_repo: UserRepository, redis: Redis) -> None:
        self.user_repo = user_repo
        self.redis = redis

    async def register(self, user_data: UserCreate) -> User:
        """
        Register a new user account.
        
        Args:
            user_data: Registration data with email, username, password
            
        Returns:
            Newly created User
            
        Raises:
            HTTPException: If email or username already exists
        """
        existing = await self.user_repo.get_by_email_or_username(
            user_data.email, user_data.username
        )
        
        if existing:
            detail = (
                "Email already registered" 
                if existing.email == user_data.email 
                else "Username already taken"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )

        return await self.user_repo.create(
            email=user_data.email,
            username=user_data.username,
            password_hash=hash_password(user_data.password),
        )

    async def login(self, username: str, password: str) -> LoginResponse:
        """
        Authenticate user and return tokens.
        
        Args:
            username: User's username
            password: Plain text password
            
        Returns:
            LoginResponse with user info and tokens
            
        Raises:
            HTTPException: If credentials invalid or account locked
        """
        user = await self.user_repo.get_by_username(username)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        if user.is_locked():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is temporarily locked",
            )

        if not verify_password(password, user.password_hash):
            user.record_failed_login()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        # Successful login - reset attempts and create tokens
        user.reset_login_attempts()
        tokens = self._create_tokens(user.id)
        await self._store_refresh_token(user.id, tokens.refresh_token)

        return LoginResponse(
            user=UserResponse.model_validate(user),
            tokens=tokens,
        )

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
        if stored_token != refresh_token:
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

    async def logout(self, user_id: int) -> None:
        """
        Logout user by revoking their refresh token.
        
        Args:
            user_id: ID of user to logout
        """
        await self.redis.delete(redis_keys.refresh_token(user_id))

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
