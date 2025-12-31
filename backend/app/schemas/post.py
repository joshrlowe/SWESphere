"""Post and comment schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.pagination import calculate_pages
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
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(
        cls,
        posts: list[PostResponse],
        total: int,
        page: int,
        per_page: int,
    ) -> "PostListResponse":
        """Create a paginated response."""
        total_pages = calculate_pages(total, per_page)
        return cls(
            items=posts,
            total=total,
            page=page,
            per_page=per_page,
            pages=total_pages,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


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

    @classmethod
    def create(
        cls,
        comments: list,
        total: int,
        page: int,
        per_page: int,
    ) -> "CommentListResponse":
        """Create a paginated response."""
        return cls(
            items=[CommentResponse.model_validate(c) for c in comments],
            total=total,
            page=page,
            per_page=per_page,
            pages=calculate_pages(total, per_page),
        )


class PostDetailResponse(PostResponse):
    """Post response with comments included."""

    comments: list[CommentResponse] = []
    comments_total: int = 0
