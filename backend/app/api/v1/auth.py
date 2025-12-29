"""Authentication routes."""

from fastapi import APIRouter, status

from app.api.deps import CurrentUser
from app.dependencies import AuthSvc
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_data: UserCreate,
    auth_service: AuthSvc,
) -> UserResponse:
    """
    Register a new user account.

    - **email**: Valid email address
    - **username**: 3-64 characters, alphanumeric and underscores only
    - **password**: 8+ characters with uppercase, lowercase, and digit
    """
    user = await auth_service.register(user_data)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and get tokens",
)
async def login(
    credentials: LoginRequest,
    auth_service: AuthSvc,
) -> LoginResponse:
    """
    Authenticate with username and password to receive access and refresh tokens.
    """
    return await auth_service.login(credentials.username, credentials.password)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthSvc,
) -> TokenResponse:
    """
    Use a refresh token to get a new access token.
    """
    return await auth_service.refresh_tokens(request.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout current user",
)
async def logout(
    current_user: CurrentUser,
    auth_service: AuthSvc,
) -> None:
    """
    Logout the current user by revoking their refresh token.
    """
    await auth_service.logout(current_user.id)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """
    Get the currently authenticated user's profile.
    """
    return UserResponse.model_validate(current_user)
