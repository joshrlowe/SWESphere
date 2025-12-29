"""User schemas for request/response validation."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, EmailStr, Field, field_validator

if TYPE_CHECKING:
    from app.models.user import User


# =============================================================================
# Base Schemas
# =============================================================================


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    username: str | None = Field(
        None, min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_]+$"
    )
    display_name: str | None = Field(None, max_length=100)
    bio: str | None = Field(None, max_length=500)
    location: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=255)


class UserPasswordUpdate(BaseModel):
    """Schema for updating password."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


# =============================================================================
# Response Schemas
# =============================================================================


class UserMinimal(BaseModel):
    """Minimal user schema (for embedding in other responses)."""

    id: int
    username: str
    display_name: str | None
    avatar_url: str | None
    is_verified: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, user: "User") -> "UserMinimal":
        """
        Create UserMinimal from a User model.
        
        Use this factory method to avoid lazy-loading issues with ORM models.
        """
        return cls(
            id=user.id,
            username=user.username,
            display_name=getattr(user, "display_name", None),
            avatar_url=getattr(user, "avatar_url", None),
            is_verified=getattr(user, "is_verified", False),
        )


class UserPublic(BaseModel):
    """Public user schema (for other users viewing a profile)."""

    id: int
    username: str
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    location: str | None = None
    website: str | None = None
    is_verified: bool = False
    followers_count: int = 0
    following_count: int = 0
    created_at: datetime

    # Populated by route when viewer is authenticated (not from model)
    is_following: bool | None = None

    model_config = {
        "from_attributes": True,
        "extra": "ignore",
    }

    @classmethod
    def from_model(cls, user: "User", is_following: bool | None = None) -> "UserPublic":
        """
        Create UserPublic from a User model.
        
        Use this factory method to avoid lazy-loading issues with ORM models.
        The is_following field is computed separately by the route.
        """
        return cls(
            id=user.id,
            username=user.username,
            display_name=getattr(user, "display_name", None),
            bio=getattr(user, "bio", None),
            avatar_url=getattr(user, "avatar_url", None),
            location=getattr(user, "location", None),
            website=getattr(user, "website", None),
            is_verified=getattr(user, "is_verified", False),
            followers_count=getattr(user, "followers_count", 0),
            following_count=getattr(user, "following_count", 0),
            created_at=user.created_at,
            is_following=is_following,
        )


class UserResponse(BaseModel):
    """Full user response schema (for authenticated user)."""

    id: int
    email: EmailStr
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    location: str | None
    website: str | None
    is_active: bool
    is_verified: bool
    email_verified: bool
    followers_count: int
    following_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Paginated Response
# =============================================================================


class UserListResponse(BaseModel):
    """Paginated user list response."""

    items: list[UserPublic]
    total: int
    page: int
    per_page: int
    pages: int

    @classmethod
    def create(
        cls,
        users: list,
        total: int,
        page: int,
        per_page: int,
    ) -> "UserListResponse":
        """Create a paginated response from a list of User models."""
        pages = _calculate_pages(total, per_page)
        items = [UserPublic.from_model(u) for u in users]
        return cls(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
        )


# =============================================================================
# Helpers
# =============================================================================


def _calculate_pages(total: int, per_page: int) -> int:
    """Calculate total number of pages for pagination."""
    if per_page <= 0:
        return 0
    return (total + per_page - 1) // per_page


# Alias for backwards compatibility
UserPublicResponse = UserPublic
