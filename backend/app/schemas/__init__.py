"""Pydantic schemas for request/response validation."""

from app.schemas.auth import (
    EmailVerificationRequest,
    LoginRequest,
    LoginResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import (
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
)
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.schemas.post import (
    CommentCreate,
    CommentListResponse,
    CommentResponse,
    PostCreate,
    PostDetailResponse,
    PostListResponse,
    PostResponse,
    PostUpdate,
)
from app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserMinimal,
    UserPublic,
    UserPublicResponse,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "RegisterRequest",
    "TokenResponse",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "EmailVerificationRequest",
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserPublic",
    "UserPublicResponse",
    "UserMinimal",
    "UserListResponse",
    # Post
    "PostCreate",
    "PostUpdate",
    "PostResponse",
    "PostListResponse",
    "PostDetailResponse",
    "CommentCreate",
    "CommentResponse",
    "CommentListResponse",
    # Notification
    "NotificationResponse",
    "NotificationListResponse",
    "UnreadCountResponse",
    # Common
    "PaginationParams",
    "MessageResponse",
    "ErrorResponse",
    "PaginatedResponse",
]
