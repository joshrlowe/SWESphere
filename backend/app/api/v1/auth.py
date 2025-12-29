"""
Authentication routes.

Handles user registration, login, logout, token refresh,
email verification, and password reset flows.
"""

from fastapi import APIRouter, Path, status

from app.api.deps import CurrentUser
from app.dependencies import AuthSvc
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


# =============================================================================
# Registration & Login
# =============================================================================


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Email or username already taken"},
        422: {"description": "Validation error"},
    },
)
async def register(
    user_data: UserCreate,
    auth_service: AuthSvc,
) -> UserResponse:
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **username**: 3-64 characters, alphanumeric and underscores only (must be unique)
    - **password**: 8+ characters with at least one uppercase, lowercase, and digit

    A verification email will be sent to confirm the email address.
    """
    user = await auth_service.register(user_data)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and get tokens",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
        403: {"description": "Account locked or disabled"},
    },
)
async def login(
    credentials: LoginRequest,
    auth_service: AuthSvc,
) -> LoginResponse:
    """
    Authenticate with username/email and password.

    Returns access and refresh tokens on success.

    - **username**: Username or email address
    - **password**: Account password

    Account will be temporarily locked after 5 failed attempts.
    """
    return await auth_service.login(credentials.username, credentials.password)


# =============================================================================
# Token Management
# =============================================================================


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    responses={
        200: {"description": "New tokens issued"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthSvc,
) -> TokenResponse:
    """
    Use a refresh token to get new access and refresh tokens.

    The old refresh token will be invalidated.
    """
    return await auth_service.refresh_tokens(request.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout current user",
    responses={
        204: {"description": "Logged out successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def logout(
    current_user: CurrentUser,
    auth_service: AuthSvc,
) -> None:
    """
    Logout the current user.

    Revokes the refresh token and invalidates the session.
    """
    await auth_service.logout(current_user.id)


# =============================================================================
# Email Verification
# =============================================================================


@router.post(
    "/verify-email/{token}",
    response_model=MessageResponse,
    summary="Verify email address",
    responses={
        200: {"description": "Email verified successfully"},
        400: {"description": "Invalid or expired token"},
    },
)
async def verify_email(
    token: str = Path(..., description="Email verification token"),
    auth_service: AuthSvc = ...,
) -> MessageResponse:
    """
    Verify a user's email address using the token from the verification email.

    The token is single-use and expires after 24 hours.
    """
    await auth_service.verify_email(token)
    return MessageResponse(message="Email verified successfully")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification email",
    responses={
        200: {"description": "Verification email sent (if applicable)"},
    },
)
async def resend_verification(
    current_user: CurrentUser,
    auth_service: AuthSvc,
) -> MessageResponse:
    """
    Resend the email verification link.

    Only works if the email is not already verified.
    """
    if current_user.email_verified:
        return MessageResponse(message="Email is already verified")

    await auth_service.send_verification_email(current_user)
    return MessageResponse(message="Verification email sent")


# =============================================================================
# Password Reset
# =============================================================================


@router.post(
    "/password-reset",
    response_model=MessageResponse,
    summary="Request password reset",
    responses={
        200: {"description": "Reset instructions sent (if email exists)"},
    },
)
async def request_password_reset(
    request: PasswordResetRequest,
    auth_service: AuthSvc,
) -> MessageResponse:
    """
    Request a password reset email.

    For security, this endpoint always returns success, even if the email
    doesn't exist. If the email is registered, a reset link will be sent.
    """
    await auth_service.request_password_reset(request.email)
    return MessageResponse(
        message="If an account exists with this email, reset instructions have been sent"
    )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    summary="Confirm password reset",
    responses={
        200: {"description": "Password reset successfully"},
        400: {"description": "Invalid or expired token"},
    },
)
async def confirm_password_reset(
    request: PasswordResetConfirm,
    auth_service: AuthSvc,
) -> MessageResponse:
    """
    Reset password using the token from the password reset email.

    - **token**: Reset token from the email link
    - **new_password**: New password (8+ chars, uppercase, lowercase, digit)

    The token is single-use and expires after 1 hour.
    All existing sessions will be invalidated.
    """
    await auth_service.reset_password(request.token, request.new_password)
    return MessageResponse(message="Password reset successfully")


# =============================================================================
# Current User
# =============================================================================


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    responses={
        200: {"description": "Current user profile"},
        401: {"description": "Not authenticated"},
    },
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """
    Get the currently authenticated user's profile.

    Returns full user information including email and account settings.
    """
    return UserResponse.model_validate(current_user)
