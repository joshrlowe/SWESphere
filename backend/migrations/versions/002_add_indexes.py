"""Add performance indexes and full-text search.

Revision ID: 002_add_indexes
Revises: 001_initial
Create Date: 2024-01-20 12:00:00.000000

Adds critical indexes for:
- Feed queries (home/explore)
- User search (case-insensitive)
- Full-text search on posts
- Notifications filtering
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_add_indexes"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add performance indexes and full-text search support."""

    # ===================
    # Posts - Feed Query Indexes
    # ===================

    # Composite index for home feed: user_id + timestamp (covering index)
    # Speeds up: SELECT * FROM posts WHERE user_id IN (...) ORDER BY created_at DESC
    op.create_index(
        "idx_posts_user_timestamp",
        "posts",
        ["user_id", "created_at"],
        postgresql_using="btree",
    )

    # Composite index for explore feed: timestamp + engagement metrics
    # Speeds up: ORDER BY created_at DESC, likes_count DESC
    op.create_index(
        "idx_posts_timestamp_engagement",
        "posts",
        ["created_at", "likes_count", "comments_count"],
        postgresql_using="btree",
    )

    # Partial index for non-deleted posts (most common filter)
    op.create_index(
        "idx_posts_active",
        "posts",
        ["created_at"],
        postgresql_where="deleted_at IS NULL",
    )

    # Engagement-based sorting for trending/explore
    # DESC order for better performance on "top posts" queries
    op.execute("""
        CREATE INDEX idx_posts_engagement_score 
        ON posts ((likes_count + comments_count * 2), created_at DESC)
        WHERE deleted_at IS NULL
    """)

    # ===================
    # Users - Search Indexes
    # ===================

    # Case-insensitive username search using functional index
    # Speeds up: WHERE LOWER(username) = LOWER('query')
    op.execute("""
        CREATE INDEX idx_users_username_lower 
        ON users (LOWER(username))
    """)

    # Case-insensitive display_name search
    op.execute("""
        CREATE INDEX idx_users_display_name_lower 
        ON users (LOWER(display_name))
        WHERE display_name IS NOT NULL
    """)

    # Trigram index for fuzzy username search (pg_trgm extension)
    # Enables: username ILIKE '%query%' or similarity matching
    op.execute("""
        CREATE EXTENSION IF NOT EXISTS pg_trgm
    """)

    op.execute("""
        CREATE INDEX idx_users_username_trgm 
        ON users USING gin (username gin_trgm_ops)
    """)

    op.execute("""
        CREATE INDEX idx_users_display_name_trgm 
        ON users USING gin (display_name gin_trgm_ops)
        WHERE display_name IS NOT NULL
    """)

    # Prefix search for autocomplete (btree with text_pattern_ops)
    op.execute("""
        CREATE INDEX idx_users_username_prefix 
        ON users (username text_pattern_ops)
    """)

    # ===================
    # Posts - Full-Text Search (PostgreSQL)
    # ===================

    # GIN index for full-text search on post body
    # Uses english text search configuration
    op.execute("""
        CREATE INDEX idx_posts_body_fts 
        ON posts USING gin(to_tsvector('english', body))
    """)

    # Optional: Add tsvector column for better FTS performance
    # This denormalizes the tsvector for faster searches
    op.execute("""
        ALTER TABLE posts 
        ADD COLUMN IF NOT EXISTS search_vector tsvector 
        GENERATED ALWAYS AS (to_tsvector('english', body)) STORED
    """)

    op.execute("""
        CREATE INDEX idx_posts_search_vector 
        ON posts USING gin(search_vector)
    """)

    # ===================
    # Notifications - Optimized Queries
    # ===================

    # Composite index for user's unread notifications
    # Speeds up: WHERE user_id = ? AND read = false ORDER BY created_at DESC
    op.create_index(
        "idx_notifications_user_read_timestamp",
        "notifications",
        ["user_id", "read", "created_at"],
        postgresql_using="btree",
    )

    # Partial index for unread notifications only
    op.create_index(
        "idx_notifications_unread",
        "notifications",
        ["user_id", "created_at"],
        postgresql_where="read = false",
    )

    # ===================
    # Post Likes - Query Optimization
    # ===================

    # Composite index for batch like checking
    # Speeds up: WHERE user_id = ? AND post_id IN (...)
    op.create_index(
        "idx_post_likes_user_post",
        "post_likes",
        ["user_id", "post_id"],
        postgresql_using="btree",
    )

    # ===================
    # Followers - Feed Generation
    # ===================

    # Composite index for getting followed user IDs
    op.create_index(
        "idx_followers_follower_followed",
        "followers",
        ["follower_id", "followed_id"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    """Remove all added indexes."""

    # Post likes
    op.drop_index("idx_post_likes_user_post")

    # Followers
    op.drop_index("idx_followers_follower_followed")

    # Notifications
    op.drop_index("idx_notifications_unread")
    op.drop_index("idx_notifications_user_read_timestamp")

    # Posts FTS
    op.drop_index("idx_posts_search_vector")
    op.execute("ALTER TABLE posts DROP COLUMN IF EXISTS search_vector")
    op.drop_index("idx_posts_body_fts")

    # Users search
    op.drop_index("idx_users_username_prefix")
    op.drop_index("idx_users_display_name_trgm")
    op.drop_index("idx_users_username_trgm")
    op.drop_index("idx_users_display_name_lower")
    op.drop_index("idx_users_username_lower")

    # Posts feed
    op.execute("DROP INDEX IF EXISTS idx_posts_engagement_score")
    op.drop_index("idx_posts_active")
    op.drop_index("idx_posts_timestamp_engagement")
    op.drop_index("idx_posts_user_timestamp")

