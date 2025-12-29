"""
Search repository for full-text and fuzzy search operations.

Provides optimized search functionality using PostgreSQL features:
- Full-text search with ts_rank scoring
- Trigram similarity for fuzzy matching
- Prefix matching for autocomplete
"""

import logging
from typing import Any, Sequence

from sqlalchemy import Float, Integer, String, case, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.post import Post
from app.models.user import User

logger = logging.getLogger(__name__)


class SearchRepository:
    """
    Repository for search operations across posts and users.

    Uses PostgreSQL full-text search and trigram similarity
    for efficient and relevant search results.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize search repository."""
        self.db = db

    # =========================================================================
    # Post Search (Full-Text)
    # =========================================================================

    async def search_posts(
        self,
        query: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Post], int]:
        """
        Search posts using PostgreSQL full-text search.

        Uses plainto_tsquery for natural language queries and
        ts_rank for relevance scoring.

        Args:
            query: Search query string
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Tuple of (posts, total_count)
        """
        if not query or not query.strip():
            return [], 0

        logger.debug(f"FTS searching posts: {query}")

        # Clean query for tsquery
        clean_query = query.strip()

        # Build tsquery - plainto_tsquery handles natural language
        # Also try prefix matching for partial words
        tsquery = func.plainto_tsquery("english", clean_query)

        # Use the stored search_vector column if available, otherwise compute
        # search_condition uses @@ operator for tsvector matching
        search_condition = Post.search_vector.op("@@")(tsquery)

        # Calculate relevance rank
        rank = func.ts_rank(Post.search_vector, tsquery)

        # Get total count
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Post)
            .where(search_condition)
            .where(Post.deleted_at.is_(None))
        )
        total = count_result.scalar() or 0

        # Get ranked results
        result = await self.db.execute(
            select(Post)
            .where(search_condition)
            .where(Post.deleted_at.is_(None))
            .options(selectinload(Post.author))
            .order_by(rank.desc(), Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all(), total

    async def search_posts_fuzzy(
        self,
        query: str,
        *,
        skip: int = 0,
        limit: int = 20,
        min_similarity: float = 0.3,
    ) -> tuple[Sequence[Post], int]:
        """
        Fuzzy search posts using trigram similarity.

        Falls back to ILIKE for simple substring matching
        when trigram extension is not available.

        Args:
            query: Search query string
            skip: Pagination offset
            limit: Maximum results
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            Tuple of (posts, total_count)
        """
        if not query or not query.strip():
            return [], 0

        clean_query = query.strip()
        search_pattern = f"%{clean_query}%"

        logger.debug(f"Fuzzy searching posts: {clean_query}")

        # Use ILIKE for compatibility, works with trigram index
        search_condition = Post.body.ilike(search_pattern)

        # Get total count
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Post)
            .where(search_condition)
            .where(Post.deleted_at.is_(None))
        )
        total = count_result.scalar() or 0

        # Get results ordered by recency (since we can't easily rank ILIKE)
        result = await self.db.execute(
            select(Post)
            .where(search_condition)
            .where(Post.deleted_at.is_(None))
            .options(selectinload(Post.author))
            .order_by(Post.likes_count.desc(), Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all(), total

    # =========================================================================
    # User Search
    # =========================================================================

    async def search_users(
        self,
        query: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[User], int]:
        """
        Search users by username and bio.

        Uses prefix match on username and contains match on bio.
        Results are ranked by follower count.

        Args:
            query: Search query string
            skip: Pagination offset
            limit: Maximum results

        Returns:
            Tuple of (users, total_count)
        """
        if not query or not query.strip():
            return [], 0

        clean_query = query.strip().lower()
        prefix_pattern = f"{clean_query}%"
        contains_pattern = f"%{clean_query}%"

        logger.debug(f"Searching users: {clean_query}")

        # Search conditions:
        # 1. Username starts with query (prefix match - most relevant)
        # 2. Username contains query
        # 3. Display name contains query
        # 4. Bio contains query
        search_condition = or_(
            func.lower(User.username).like(prefix_pattern),
            func.lower(User.username).like(contains_pattern),
            func.lower(User.display_name).like(contains_pattern),
            User.bio.ilike(contains_pattern),
        )

        # Get total count
        count_result = await self.db.execute(
            select(func.count())
            .select_from(User)
            .where(search_condition)
            .where(User.is_active.is_(True))
            .where(User.deleted_at.is_(None))
        )
        total = count_result.scalar() or 0

        # Relevance scoring:
        # - Prefix match on username: highest priority
        # - Contains match on username: medium priority
        # - Followers count: tiebreaker
        prefix_match_score = case(
            (func.lower(User.username).like(prefix_pattern), literal(100)),
            (func.lower(User.username).like(contains_pattern), literal(50)),
            (func.lower(User.display_name).like(contains_pattern), literal(25)),
            else_=literal(0),
        )

        # Get ranked results
        result = await self.db.execute(
            select(User)
            .where(search_condition)
            .where(User.is_active.is_(True))
            .where(User.deleted_at.is_(None))
            .order_by(
                prefix_match_score.desc(),
                User.followers_count.desc(),
                User.username,
            )
            .offset(skip)
            .limit(limit)
        )

        return result.scalars().all(), total

    async def autocomplete_users(
        self,
        prefix: str,
        *,
        limit: int = 10,
        exclude_ids: set[int] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fast autocomplete for @mentions.

        Returns lightweight user data for autocomplete UI.
        Uses prefix index for fast lookups.

        Args:
            prefix: Username prefix to match
            limit: Maximum results
            exclude_ids: User IDs to exclude from results

        Returns:
            List of dicts with id, username, display_name, avatar_url
        """
        if not prefix or not prefix.strip():
            return []

        clean_prefix = prefix.strip().lstrip("@").lower()

        if len(clean_prefix) < 1:
            return []

        logger.debug(f"Autocomplete users: @{clean_prefix}")

        # Prefix pattern for LIKE
        prefix_pattern = f"{clean_prefix}%"

        # Build query
        query = (
            select(
                User.id,
                User.username,
                User.display_name,
                User.avatar_url,
                User.is_verified,
            )
            .where(func.lower(User.username).like(prefix_pattern))
            .where(User.is_active.is_(True))
            .where(User.deleted_at.is_(None))
            .order_by(User.followers_count.desc(), User.username)
            .limit(limit)
        )

        if exclude_ids:
            query = query.where(User.id.notin_(exclude_ids))

        result = await self.db.execute(query)

        return [
            {
                "id": row.id,
                "username": row.username,
                "display_name": row.display_name,
                "avatar_url": row.avatar_url,
                "is_verified": row.is_verified,
            }
            for row in result.fetchall()
        ]

    async def autocomplete_hashtags(
        self,
        prefix: str,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Autocomplete hashtags from post content.

        Extracts hashtags from posts matching the prefix.

        Args:
            prefix: Hashtag prefix to match (without #)
            limit: Maximum results

        Returns:
            List of dicts with hashtag and usage count
        """
        if not prefix or not prefix.strip():
            return []

        clean_prefix = prefix.strip().lstrip("#").lower()

        if len(clean_prefix) < 1:
            return []

        logger.debug(f"Autocomplete hashtags: #{clean_prefix}")

        # Use regex to extract hashtags from posts
        # This is a simple implementation - for production, consider
        # maintaining a separate hashtags table
        hashtag_pattern = f"#({clean_prefix}[a-zA-Z0-9_]*)"

        result = await self.db.execute(
            text("""
                SELECT 
                    LOWER(match[1]) as hashtag,
                    COUNT(*) as usage_count
                FROM 
                    posts,
                    regexp_matches(body, :pattern, 'gi') as match
                WHERE 
                    deleted_at IS NULL
                GROUP BY 
                    LOWER(match[1])
                ORDER BY 
                    usage_count DESC
                LIMIT :limit
            """),
            {"pattern": hashtag_pattern, "limit": limit},
        )

        return [
            {"hashtag": f"#{row.hashtag}", "count": row.usage_count}
            for row in result.fetchall()
        ]

    # =========================================================================
    # Combined Search
    # =========================================================================

    async def search_all(
        self,
        query: str,
        *,
        posts_limit: int = 5,
        users_limit: int = 5,
    ) -> dict[str, Any]:
        """
        Search across all content types.

        Useful for unified search UI showing mixed results.

        Args:
            query: Search query
            posts_limit: Max posts to return
            users_limit: Max users to return

        Returns:
            Dict with 'posts', 'users', and counts
        """
        if not query or not query.strip():
            return {"posts": [], "users": [], "posts_total": 0, "users_total": 0}

        # Run searches (using fuzzy for SQLite compatibility)
        posts, posts_total = await self.search_posts_fuzzy(query, limit=posts_limit)
        users, users_total = await self.search_users(query, limit=users_limit)

        return {
            "posts": posts,
            "users": users,
            "posts_total": posts_total,
            "users_total": users_total,
        }

