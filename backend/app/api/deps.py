"""
API route dependencies for authentication and authorization.

This module provides FastAPI dependencies for extracting and validating
the current user from JWT tokens in request headers.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_access_token
from app.dependencies import DBSession
from app.models.user import User
from app.repositories.user_repository import UserRepository


# HTTP Bearer scheme - auto_error=False allows optional auth
_bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Raised when authentication fails."""
    
    def __init__(self, detail: str, include_header: bool = True) -> None:
        headers = {"WWW-Authenticate": "Bearer"} if include_header else None
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=headers,
        )


class AuthorizationError(HTTPException):
    """Raised when user lacks permission."""
    
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def _extract_user_from_token(
    db: DBSession,
    credentials: HTTPAuthorizationCredentials | None,
    *,
    raise_on_failure: bool,
) -> User | None:
    """
    Core logic for extracting user from JWT token.
    
    Args:
        db: Database session
        credentials: Bearer token credentials from request
        raise_on_failure: If True, raises HTTPException on any failure.
                          If False, returns None on failure.
    
    Returns:
        User if authenticated, None if not (when raise_on_failure=False)
    
    Raises:
        AuthenticationError: When authentication fails and raise_on_failure=True
        AuthorizationError: When user is disabled and raise_on_failure=True
    """
    # No credentials provided
    if not credentials:
        if raise_on_failure:
            raise AuthenticationError("Not authenticated")
        return None
    
    # Verify token and extract user ID
    user_id = verify_access_token(credentials.credentials)
    if not user_id:
        if raise_on_failure:
            raise AuthenticationError("Invalid or expired token")
        return None
    
    # Fetch user from database
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(int(user_id))
    
    if not user:
        if raise_on_failure:
            raise AuthenticationError("User not found", include_header=False)
        return None
    
    # Check if account is active
    if not user.is_active:
        if raise_on_failure:
            raise AuthorizationError("User account is disabled")
        return None
    
    return user


async def get_current_user(
    db: DBSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, 
        Depends(_bearer_scheme)
    ] = None,
) -> User:
    """
    Get the current authenticated user (required).
    
    Use this dependency when authentication is mandatory.
    Raises HTTPException if not authenticated or user is inactive.
    
    Example:
        @router.get("/profile")
        async def get_profile(user: CurrentUser) -> UserResponse:
            return UserResponse.model_validate(user)
    """
    user = await _extract_user_from_token(db, credentials, raise_on_failure=True)
    assert user is not None  # For type checker - raise_on_failure=True guarantees this
    return user


async def get_current_user_optional(
    db: DBSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, 
        Depends(_bearer_scheme)
    ] = None,
) -> User | None:
    """
    Get the current user if authenticated, None otherwise.
    
    Use this dependency when authentication is optional.
    Does not raise exceptions - just returns None if not authenticated.
    
    Example:
        @router.get("/posts")
        async def list_posts(user: OptionalUser) -> list[Post]:
            if user:
                # Personalized response
                ...
            else:
                # Public response
                ...
    """
    return await _extract_user_from_token(db, credentials, raise_on_failure=False)


# Type aliases for clean dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
