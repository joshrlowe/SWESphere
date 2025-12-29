"""
SQLAlchemy models for SWESphere.

This module exports all models and association tables for the application.
Import models from this module to ensure proper initialization order.

Association Tables:
    - followers: Many-to-many relationship between users (follower/followed)
    - post_likes: Many-to-many relationship between users and liked posts

Models:
    - User: User accounts and profiles
    - Post: User posts/tweets
    - Comment: Comments on posts with nested reply support
    - Notification: User notifications with various types

Mixins:
    - TimestampMixin: Adds created_at/updated_at
    - SoftDeleteMixin: Adds soft delete functionality
    - BaseModelMixin: Combined common functionality
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Table, func

from app.db.base import Base

# ===================
# Association Tables
# ===================

# Followers association table (many-to-many self-referential)
followers = Table(
    "followers",
    Base.metadata,
    Column(
        "follower_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        doc="User who is following",
    ),
    Column(
        "followed_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        doc="User being followed",
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the follow relationship was created",
    ),
    # Indexes for efficient queries
    Index("ix_followers_follower_id", "follower_id"),
    Index("ix_followers_followed_id", "followed_id"),
    Index("ix_followers_created_at", "created_at"),
)


# Post likes association table (many-to-many between users and posts)
post_likes = Table(
    "post_likes",
    Base.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        doc="User who liked the post",
    ),
    Column(
        "post_id",
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True,
        doc="Post that was liked",
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the like was created",
    ),
    # Indexes for efficient queries
    Index("ix_post_likes_user_id", "user_id"),
    Index("ix_post_likes_post_id", "post_id"),
    Index("ix_post_likes_created_at", "created_at"),
)


# ===================
# Model Imports
# ===================

# Import models after association tables to avoid circular imports
from app.models.comment import Comment
from app.models.mixins import (
    BaseModelMixin,
    ReprMixin,
    SoftDeleteMixin,
    TimestampMixin,
    ToDictMixin,
)
from app.models.notification import Notification, NotificationType
from app.models.post import Post
from app.models.user import User

# ===================
# Exports
# ===================

__all__ = [
    # Association tables
    "followers",
    "post_likes",
    # Models
    "User",
    "Post",
    "Comment",
    "Notification",
    # Enums
    "NotificationType",
    # Mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    "BaseModelMixin",
    "ReprMixin",
    "ToDictMixin",
]
