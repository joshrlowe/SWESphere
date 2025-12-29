"""User schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


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

    display_name: str | None = Field(None, max_length=100)
    bio: str | None = Field(None, max_length=500)
    location: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=255)


class UserPasswordUpdate(BaseModel):
    """Schema for updating password."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


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


class UserPublic(BaseModel):
    """Public user schema (for other users viewing a profile)."""

    id: int
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    location: str | None
    website: str | None
    is_verified: bool
    followers_count: int
    following_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserMinimal(BaseModel):
    """Minimal user schema (for embedding in other responses)."""

    id: int
    username: str
    display_name: str | None
    avatar_url: str | None
    is_verified: bool

    model_config = {"from_attributes": True}

