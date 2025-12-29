"""Comment model with nested replies support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import BaseModelMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.user import User


class Comment(Base, BaseModelMixin, SoftDeleteMixin):
    """
    Comment model for post comments with nested reply support.
    
    Attributes:
        id: Primary key
        body: Comment content (max 500 characters)
        user_id: Foreign key to comment author
        post_id: Foreign key to parent post
        parent_id: Foreign key to parent comment (for nested replies)
    
    Relationships:
        author: User who wrote the comment
        post: Post this comment belongs to
        parent: Parent comment (if this is a reply)
        replies: Child comments replying to this comment
    
    The comment tree supports unlimited nesting depth, but the UI typically
    displays only 2-3 levels for readability.
    """

    __tablename__ = "comments"

    # ===================
    # Primary Key
    # ===================
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ===================
    # Content
    # ===================
    body: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Comment content, max 500 characters",
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

    post_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Parent comment ID for nested replies",
    )

    # ===================
    # Denormalized
    # ===================
    replies_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Cached count of direct replies",
    )

    depth: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Nesting depth (0 for top-level comments)",
    )

    # ===================
    # Relationships
    # ===================
    author: Mapped["User"] = relationship(
        "User",
        back_populates="comments",
        lazy="selectin",
    )

    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="comments",
        lazy="selectin",
    )

    # Self-referential for nested comments
    parent: Mapped["Comment | None"] = relationship(
        "Comment",
        remote_side="Comment.id",
        back_populates="replies",
        lazy="selectin",
    )

    replies: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Comment.created_at.asc()",
    )

    # ===================
    # Indexes
    # ===================
    __table_args__ = (
        # For fetching post's comments
        Index("ix_comments_post_id_created_at", "post_id", "created_at"),
        # For fetching user's comments
        Index("ix_comments_user_id_created_at", "user_id", "created_at"),
        # For fetching replies to a comment
        Index("ix_comments_parent_id_created_at", "parent_id", "created_at"),
    )

    # ===================
    # Methods
    # ===================
    @property
    def is_reply(self) -> bool:
        """Check if this comment is a reply to another comment."""
        return self.parent_id is not None

    @property
    def is_top_level(self) -> bool:
        """Check if this is a top-level comment (not a reply)."""
        return self.parent_id is None

    def increment_replies(self) -> None:
        """Increment the replies count."""
        self.replies_count += 1

    def decrement_replies(self) -> None:
        """Decrement the replies count."""
        self.replies_count = max(0, self.replies_count - 1)

    def get_thread(self) -> list["Comment"]:
        """
        Get the full thread from root to this comment.
        
        Returns:
            List of comments from root to this comment (inclusive)
        """
        thread = [self]
        current = self
        while current.parent is not None:
            thread.insert(0, current.parent)
            current = current.parent
        return thread

    def get_root(self) -> "Comment":
        """
        Get the root (top-level) comment of this thread.
        
        Returns:
            The root comment
        """
        if self.parent is None:
            return self
        return self.parent.get_root()

    def get_all_descendants(self) -> list["Comment"]:
        """
        Get all descendant comments (children, grandchildren, etc).
        
        Returns:
            Flat list of all descendant comments
        """
        descendants = []
        for reply in self.replies:
            descendants.append(reply)
            descendants.extend(reply.get_all_descendants())
        return descendants

    def to_dict(
        self,
        include_author: bool = True,
        include_replies: bool = False,
        max_depth: int = 2,
    ) -> dict[str, Any]:
        """
        Convert comment to dictionary for API responses.
        
        Args:
            include_author: Include author details
            include_replies: Include nested replies
            max_depth: Maximum nesting depth for replies
            
        Returns:
            Dictionary representation
        """
        data: dict[str, Any] = {
            "id": self.id,
            "body": self.body,
            "user_id": self.user_id,
            "post_id": self.post_id,
            "parent_id": self.parent_id,
            "is_reply": self.is_reply,
            "depth": self.depth,
            "replies_count": self.replies_count,
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

        if include_replies and self.depth < max_depth:
            data["replies"] = [
                reply.to_dict(
                    include_author=include_author,
                    include_replies=True,
                    max_depth=max_depth,
                )
                for reply in self.replies
                if not reply.is_deleted
            ]

        return data

    def __repr__(self) -> str:
        return (
            f"<Comment(id={self.id}, post_id={self.post_id}, "
            f"user_id={self.user_id}, body={self.body[:20]!r}...)>"
        )
