"""Initial database schema.

Revision ID: 001_initial
Revises:
Create Date: 2024-01-15 12:00:00.000000

Creates all core tables:
- users: User accounts and profiles
- posts: User posts/tweets
- comments: Comments on posts
- notifications: User notifications
- followers: User follow relationships
- post_likes: Post like relationships
"""

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all tables and indexes."""

    # ===================
    # Users Table
    # ===================
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        # Authentication
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        # Profile
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        # Status flags
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False, default=False),
        # Security
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, default=0),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        # Denormalized counts
        sa.Column("followers_count", sa.Integer(), nullable=False, default=0),
        sa.Column("following_count", sa.Integer(), nullable=False, default=0),
        sa.Column("posts_count", sa.Integer(), nullable=False, default=0),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )

    # Users indexes
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_created_at", "users", ["created_at"])
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])

    # ===================
    # Posts Table
    # ===================
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), nullable=False),
        # Content
        sa.Column("body", sa.String(280), nullable=False),
        sa.Column("media_url", sa.String(500), nullable=True),
        sa.Column("media_type", sa.String(50), nullable=True),
        # Foreign keys
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reply_to_id", sa.Integer(), nullable=True),
        sa.Column("repost_of_id", sa.Integer(), nullable=True),
        # Denormalized counts
        sa.Column("likes_count", sa.Integer(), nullable=False, default=0),
        sa.Column("comments_count", sa.Integer(), nullable=False, default=0),
        sa.Column("reposts_count", sa.Integer(), nullable=False, default=0),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reply_to_id"], ["posts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["repost_of_id"], ["posts.id"], ondelete="SET NULL"),
    )

    # Posts indexes
    op.create_index("ix_posts_id", "posts", ["id"])
    op.create_index("ix_posts_user_id", "posts", ["user_id"])
    op.create_index("ix_posts_reply_to_id", "posts", ["reply_to_id"])
    op.create_index("ix_posts_created_at", "posts", ["created_at"])
    op.create_index("ix_posts_user_id_created_at", "posts", ["user_id", "created_at"])
    op.create_index("ix_posts_created_at_likes", "posts", ["created_at", "likes_count"])
    op.create_index("ix_posts_deleted_at", "posts", ["deleted_at"])

    # ===================
    # Comments Table
    # ===================
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), nullable=False),
        # Content
        sa.Column("body", sa.String(500), nullable=False),
        # Foreign keys
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        # Denormalized
        sa.Column("replies_count", sa.Integer(), nullable=False, default=0),
        sa.Column("depth", sa.Integer(), nullable=False, default=0),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["comments.id"], ondelete="CASCADE"),
    )

    # Comments indexes
    op.create_index("ix_comments_id", "comments", ["id"])
    op.create_index("ix_comments_user_id", "comments", ["user_id"])
    op.create_index("ix_comments_post_id", "comments", ["post_id"])
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"])
    op.create_index(
        "ix_comments_post_id_created_at", "comments", ["post_id", "created_at"]
    )
    op.create_index(
        "ix_comments_user_id_created_at", "comments", ["user_id", "created_at"]
    )
    op.create_index(
        "ix_comments_parent_id_created_at", "comments", ["parent_id", "created_at"]
    )

    # ===================
    # Notifications Table
    # ===================
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        # Notification details
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, default="{}"),
        sa.Column("read", sa.Boolean(), nullable=False, default=False),
        # Foreign keys
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
    )

    # Notifications indexes
    op.create_index("ix_notifications_id", "notifications", ["id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_actor_id", "notifications", ["actor_id"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_read", "notifications", ["read"])
    op.create_index(
        "ix_notifications_user_id_created_at",
        "notifications",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_notifications_user_id_read", "notifications", ["user_id", "read"]
    )
    op.create_index(
        "ix_notifications_user_id_type", "notifications", ["user_id", "type"]
    )

    # ===================
    # Followers Association Table
    # ===================
    op.create_table(
        "followers",
        sa.Column("follower_id", sa.Integer(), nullable=False),
        sa.Column("followed_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Constraints
        sa.PrimaryKeyConstraint("follower_id", "followed_id"),
        sa.ForeignKeyConstraint(["follower_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["followed_id"], ["users.id"], ondelete="CASCADE"),
    )

    # Followers indexes
    op.create_index("ix_followers_follower_id", "followers", ["follower_id"])
    op.create_index("ix_followers_followed_id", "followers", ["followed_id"])
    op.create_index("ix_followers_created_at", "followers", ["created_at"])

    # ===================
    # Post Likes Association Table
    # ===================
    op.create_table(
        "post_likes",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Constraints
        sa.PrimaryKeyConstraint("user_id", "post_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
    )

    # Post likes indexes
    op.create_index("ix_post_likes_user_id", "post_likes", ["user_id"])
    op.create_index("ix_post_likes_post_id", "post_likes", ["post_id"])
    op.create_index("ix_post_likes_created_at", "post_likes", ["created_at"])


def downgrade() -> None:
    """Drop all tables."""
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table("post_likes")
    op.drop_table("followers")
    op.drop_table("notifications")
    op.drop_table("comments")
    op.drop_table("posts")
    op.drop_table("users")
