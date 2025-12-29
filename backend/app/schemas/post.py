"""Post and comment schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.user import UserMinimal


class PostBase(BaseModel):
    """Base post schema."""

    body: str = Field(..., min_length=1, max_length=280)


class PostCreate(PostBase):
    """Schema for creating a post."""

    media_url: str | None = None
    media_type: str | None = None
    reply_to_id: int | None = None


class PostUpdate(BaseModel):
    """Schema for updating a post."""

    body: str | None = Field(None, min_length=1, max_length=280)


class PostResponse(BaseModel):
    """Post response schema."""

    id: int
    body: str
    media_url: str | None
    media_type: str | None
    author: UserMinimal
    reply_to_id: int | None
    repost_of_id: int | None
    likes_count: int
    comments_count: int
    replies_count: int
    created_at: datetime
    updated_at: datetime

    # For authenticated users - whether they liked this post
    is_liked: bool = False

    model_config = {"from_attributes": True}


class PostListResponse(BaseModel):
    """Paginated post list response."""

    items: list[PostResponse]
    total: int
    page: int
    per_page: int
    pages: int


class CommentBase(BaseModel):
    """Base comment schema."""

    body: str = Field(..., min_length=1, max_length=500)


class CommentCreate(CommentBase):
    """Schema for creating a comment."""

    parent_id: int | None = None


class CommentResponse(BaseModel):
    """Comment response schema."""

    id: int
    body: str
    author: UserMinimal
    post_id: int
    parent_id: int | None
    replies_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommentListResponse(BaseModel):
    """Paginated comment list response."""

    items: list[CommentResponse]
    total: int
    page: int
    per_page: int
    pages: int

