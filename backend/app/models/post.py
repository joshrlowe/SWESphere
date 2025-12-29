"""Post model with likes and comments support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import BaseModelMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.user import User


class Post(Base, BaseModelMixin, SoftDeleteMixin):
    """
    Post model representing a user's tweet/post.
    
    Attributes:
        id: Primary key
        body: Post content (max 280 characters)
        media_url: Optional media attachment URL
        media_type: Type of media (image, video, gif)
        
        user_id: Foreign key to author
        reply_to_id: Foreign key to parent post (for replies)
        repost_of_id: Foreign key to original post (for reposts)
        
        likes_count: Denormalized count of likes
        comments_count: Denormalized count of comments
        reposts_count: Denormalized count of reposts
    
    Relationships:
        author: User who created the post
        comments: Comments on this post
        liked_by: Users who liked this post
        reply_to: Parent post (if this is a reply)
        replies: Reply posts to this post
    """

    __tablename__ = "posts"

    # ===================
    # Primary Key
    # ===================
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ===================
    # Content
    # ===================
    body: Mapped[str] = mapped_column(
        String(280),
        nullable=False,
        doc="Post content, max 280 characters",
    )
    media_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="URL to attached media",
    )
    media_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Type of media: image, video, gif",
    )

    # ===================
    # Foreign Keys
    # ===================
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reply_to_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Parent post ID if this is a reply",
    )

    repost_of_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("posts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Original post ID if this is a repost",
    )

    # ===================
    # Denormalized Counts
    # ===================
    likes_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Cached count of likes",
    )
    comments_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Cached count of comments",
    )
    reposts_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Cached count of reposts",
    )

    # ===================
    # Relationships
    # ===================
    author: Mapped["User"] = relationship(
        "User",
        back_populates="posts",
        lazy="selectin",
    )

    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="post",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Comment.created_at.asc()",
    )

    # Users who liked this post
    liked_by: Mapped[list["User"]] = relationship(
        "User",
        secondary="post_likes",
        back_populates="liked_posts",
        lazy="selectin",
    )

    # Self-referential for replies
    reply_to: Mapped["Post | None"] = relationship(
        "Post",
        remote_side="Post.id",
        foreign_keys=[reply_to_id],
        back_populates="replies",
        lazy="selectin",
    )

    replies: Mapped[list["Post"]] = relationship(
        "Post",
        back_populates="reply_to",
        foreign_keys=[reply_to_id],
        lazy="selectin",
        order_by="Post.created_at.asc()",
    )

    # Self-referential for reposts
    repost_of: Mapped["Post | None"] = relationship(
        "Post",
        remote_side="Post.id",
        foreign_keys=[repost_of_id],
        lazy="selectin",
    )

    # ===================
    # Indexes
    # ===================
    __table_args__ = (
        # For user's posts timeline
        Index("ix_posts_user_id_created_at", "user_id", "created_at"),
        # For trending/popular posts
        Index("ix_posts_created_at_likes", "created_at", "likes_count"),
        # For feed queries
        Index("ix_posts_created_at", "created_at"),
        # Note: reply_to_id and repost_of_id already have index=True on their columns
    )

    # ===================
    # Methods
    # ===================
    @property
    def is_reply(self) -> bool:
        """Check if this post is a reply to another post."""
        return self.reply_to_id is not None

    @property
    def is_repost(self) -> bool:
        """Check if this post is a repost."""
        return self.repost_of_id is not None

    @property
    def replies_count(self) -> int:
        """Get the number of replies to this post."""
        return len(self.replies)

    def increment_likes(self) -> None:
        """Increment the likes count."""
        self.likes_count += 1

    def decrement_likes(self) -> None:
        """Decrement the likes count."""
        self.likes_count = max(0, self.likes_count - 1)

    def increment_comments(self) -> None:
        """Increment the comments count."""
        self.comments_count += 1

    def decrement_comments(self) -> None:
        """Decrement the comments count."""
        self.comments_count = max(0, self.comments_count - 1)

    def increment_reposts(self) -> None:
        """Increment the reposts count."""
        self.reposts_count += 1

    def decrement_reposts(self) -> None:
        """Decrement the reposts count."""
        self.reposts_count = max(0, self.reposts_count - 1)

    def to_dict(
        self,
        include_author: bool = True,
        include_counts: bool = True,
        current_user_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Convert post to dictionary for API responses.
        
        Args:
            include_author: Include author details
            include_counts: Include like/comment/repost counts
            current_user_id: Current user's ID for is_liked check
            
        Returns:
            Dictionary representation
        """
        data: dict[str, Any] = {
            "id": self.id,
            "body": self.body,
            "media_url": self.media_url,
            "media_type": self.media_type,
            "user_id": self.user_id,
            "reply_to_id": self.reply_to_id,
            "repost_of_id": self.repost_of_id,
            "is_reply": self.is_reply,
            "is_repost": self.is_repost,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_author and self.author:
            data["author"] = {
                "id": self.author.id,
                "username": self.author.username,
                "display_name": self.author.display_name,
                "avatar_url": self.author.avatar,
                "is_verified": self.author.is_verified,
            }

        if include_counts:
            data["likes_count"] = self.likes_count
            data["comments_count"] = self.comments_count
            data["reposts_count"] = self.reposts_count
            data["replies_count"] = self.replies_count

        # Check if current user has liked this post
        if current_user_id is not None:
            data["is_liked"] = any(
                user.id == current_user_id for user in self.liked_by
            )
        else:
            data["is_liked"] = False

        return data

    def __repr__(self) -> str:
        return f"<Post(id={self.id}, user_id={self.user_id}, body={self.body[:20]!r}...)>"
