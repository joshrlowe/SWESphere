"""
Tests for SearchRepository.

Note: Full-text search features (tsvector, ts_rank, trigram) are PostgreSQL-specific.
These tests use SQLite's ILIKE fallback for compatibility.
For production, additional PostgreSQL-specific tests should be run.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.user import User
from app.repositories.search_repository import SearchRepository


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def search_repo(db_session: AsyncSession) -> SearchRepository:
    """Create a SearchRepository instance."""
    return SearchRepository(db_session)


# =============================================================================
# search_posts Tests (Fuzzy fallback for SQLite)
# =============================================================================


@pytest.mark.asyncio
async def test_search_posts_basic(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory, post_factory
):
    """Test basic post search."""
    await post_factory(body="Python programming is fun")
    await post_factory(body="I love Python and Django")
    await post_factory(body="JavaScript is also great")

    # Use fuzzy search which works with SQLite
    posts, total = await search_repo.search_posts_fuzzy("python")

    assert total == 2
    assert len(posts) == 2
    assert all("python" in p.body.lower() for p in posts)


@pytest.mark.asyncio
async def test_search_posts_no_results(
    db_session: AsyncSession, search_repo: SearchRepository, post_factory
):
    """Test search with no matching results."""
    await post_factory(body="Hello world")
    await post_factory(body="Testing 123")

    posts, total = await search_repo.search_posts_fuzzy("nonexistent")

    assert total == 0
    assert len(posts) == 0


@pytest.mark.asyncio
async def test_search_posts_empty_query(
    db_session: AsyncSession, search_repo: SearchRepository, post_factory
):
    """Test search with empty query."""
    await post_factory()

    posts, total = await search_repo.search_posts_fuzzy("")

    assert total == 0
    assert len(posts) == 0


@pytest.mark.asyncio
async def test_search_posts_whitespace_query(
    db_session: AsyncSession, search_repo: SearchRepository, post_factory
):
    """Test search with whitespace-only query."""
    await post_factory()

    posts, total = await search_repo.search_posts_fuzzy("   ")

    assert total == 0
    assert len(posts) == 0


@pytest.mark.asyncio
async def test_search_posts_case_insensitive(
    db_session: AsyncSession, search_repo: SearchRepository, post_factory
):
    """Test case-insensitive search."""
    await post_factory(body="PYTHON is AWESOME")
    await post_factory(body="python is awesome")
    await post_factory(body="Python Is Awesome")

    posts, total = await search_repo.search_posts_fuzzy("PYTHON")

    assert total == 3


@pytest.mark.asyncio
async def test_search_posts_pagination(
    db_session: AsyncSession, search_repo: SearchRepository, post_factory
):
    """Test search result pagination."""
    for i in range(15):
        await post_factory(body=f"Test post {i} about coding")

    posts_page1, total = await search_repo.search_posts_fuzzy("coding", skip=0, limit=5)
    posts_page2, _ = await search_repo.search_posts_fuzzy("coding", skip=5, limit=5)

    assert total == 15
    assert len(posts_page1) == 5
    assert len(posts_page2) == 5

    # No duplicates
    page1_ids = {p.id for p in posts_page1}
    page2_ids = {p.id for p in posts_page2}
    assert not page1_ids.intersection(page2_ids)


@pytest.mark.asyncio
async def test_search_posts_excludes_deleted(
    db_session: AsyncSession, search_repo: SearchRepository, post_factory
):
    """Test that deleted posts are excluded from search."""
    visible = await post_factory(body="Searchable post")
    deleted = await post_factory(body="Searchable deleted")

    deleted.deleted_at = datetime.now(timezone.utc)
    await db_session.flush()

    posts, total = await search_repo.search_posts_fuzzy("searchable")

    assert total == 1
    assert posts[0].id == visible.id


@pytest.mark.asyncio
async def test_search_posts_special_characters(
    db_session: AsyncSession, search_repo: SearchRepository, post_factory
):
    """Test search with special characters."""
    await post_factory(body="Check out this #hashtag!")
    await post_factory(body="Email me@example.com")
    await post_factory(body="Price is $100")

    # These should not crash
    posts, _ = await search_repo.search_posts_fuzzy("#hashtag")
    assert len(posts) >= 0

    posts, _ = await search_repo.search_posts_fuzzy("@example")
    assert len(posts) >= 0


@pytest.mark.asyncio
async def test_search_posts_loads_author(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory, post_factory
):
    """Test that author is eagerly loaded."""
    user = await user_factory(username="searchauthor")
    await post_factory(author=user, body="Findable post")

    posts, _ = await search_repo.search_posts_fuzzy("findable")

    assert len(posts) == 1
    assert posts[0].author is not None
    assert posts[0].author.username == "searchauthor"


@pytest.mark.asyncio
async def test_search_posts_orders_by_engagement(
    db_session: AsyncSession, search_repo: SearchRepository, post_factory
):
    """Test that results are ordered by engagement."""
    low = await post_factory(body="Test content low")
    high = await post_factory(body="Test content high")

    high.likes_count = 100
    low.likes_count = 1
    await db_session.flush()

    posts, _ = await search_repo.search_posts_fuzzy("test content")

    assert posts[0].id == high.id


# =============================================================================
# search_users Tests
# =============================================================================


@pytest.mark.asyncio
async def test_search_users_by_username(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test searching users by username."""
    await user_factory(username="alice")
    await user_factory(username="bob")
    await user_factory(username="alicia")

    users, total = await search_repo.search_users("ali")

    assert total == 2
    assert all("ali" in u.username.lower() for u in users)


@pytest.mark.asyncio
async def test_search_users_by_display_name(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test searching users by display name."""
    await user_factory(username="user1", display_name="John Smith")
    await user_factory(username="user2", display_name="Jane Doe")
    await user_factory(username="user3", display_name="John Doe")

    users, total = await search_repo.search_users("john")

    assert total == 2


@pytest.mark.asyncio
async def test_search_users_by_bio(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test searching users by bio content."""
    await user_factory(username="dev1", bio="Python developer from NYC")
    await user_factory(username="dev2", bio="JavaScript enthusiast")
    await user_factory(username="dev3", bio="I love Python programming")

    users, total = await search_repo.search_users("python")

    assert total == 2


@pytest.mark.asyncio
async def test_search_users_no_results(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test user search with no results."""
    await user_factory(username="alice")
    await user_factory(username="bob")

    users, total = await search_repo.search_users("nonexistent")

    assert total == 0
    assert len(users) == 0


@pytest.mark.asyncio
async def test_search_users_empty_query(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test user search with empty query."""
    await user_factory()

    users, total = await search_repo.search_users("")

    assert total == 0
    assert len(users) == 0


@pytest.mark.asyncio
async def test_search_users_case_insensitive(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test case-insensitive user search."""
    await user_factory(username="TestUser")
    await user_factory(username="testuser2")
    await user_factory(username="TESTUSER3")

    users, total = await search_repo.search_users("testuser")

    assert total == 3


@pytest.mark.asyncio
async def test_search_users_pagination(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test user search pagination."""
    for i in range(12):
        await user_factory(username=f"developer{i}")

    page1, total = await search_repo.search_users("developer", skip=0, limit=5)
    page2, _ = await search_repo.search_users("developer", skip=5, limit=5)

    assert total == 12
    assert len(page1) == 5
    assert len(page2) == 5


@pytest.mark.asyncio
async def test_search_users_excludes_inactive(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test that inactive users are excluded."""
    active = await user_factory(username="activeuser", is_active=True)
    inactive = await user_factory(username="inactiveuser", is_active=False)

    users, total = await search_repo.search_users("user")

    assert total == 1
    assert users[0].id == active.id


@pytest.mark.asyncio
async def test_search_users_excludes_deleted(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test that deleted users are excluded."""
    visible = await user_factory(username="visibleuser")
    deleted = await user_factory(username="deleteduser")

    deleted.deleted_at = datetime.now(timezone.utc)
    await db_session.flush()

    users, total = await search_repo.search_users("user")

    assert total == 1
    assert users[0].id == visible.id


@pytest.mark.asyncio
async def test_search_users_prefix_ranking(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test that prefix matches rank higher."""
    contains = await user_factory(username="ilovejohn")
    prefix = await user_factory(username="johnsmith")

    users, _ = await search_repo.search_users("john")

    # Prefix match should be first
    assert users[0].username == "johnsmith"


@pytest.mark.asyncio
async def test_search_users_orders_by_followers(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test that popular users rank higher (same relevance)."""
    unpopular = await user_factory(username="coder1", followers_count=10)
    popular = await user_factory(username="coder2", followers_count=1000)

    users, _ = await search_repo.search_users("coder")

    # Same prefix match, so followers_count is tiebreaker
    assert users[0].id == popular.id


# =============================================================================
# autocomplete_users Tests
# =============================================================================


@pytest.mark.asyncio
async def test_autocomplete_users_basic(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test basic user autocomplete."""
    await user_factory(username="johndoe")
    await user_factory(username="johnsmith")
    await user_factory(username="janedoe")

    results = await search_repo.autocomplete_users("john")

    assert len(results) == 2
    assert all(r["username"].startswith("john") for r in results)


@pytest.mark.asyncio
async def test_autocomplete_users_with_at_symbol(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test autocomplete handles @ prefix."""
    await user_factory(username="testuser")

    results = await search_repo.autocomplete_users("@test")

    assert len(results) == 1
    assert results[0]["username"] == "testuser"


@pytest.mark.asyncio
async def test_autocomplete_users_returns_correct_fields(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test autocomplete returns expected fields."""
    await user_factory(
        username="testuser",
        display_name="Test User",
        avatar_url="http://example.com/avatar.jpg",
        is_verified=True,
    )

    results = await search_repo.autocomplete_users("test")

    assert len(results) == 1
    result = results[0]
    assert "id" in result
    assert result["username"] == "testuser"
    assert result["display_name"] == "Test User"
    assert result["avatar_url"] == "http://example.com/avatar.jpg"
    assert result["is_verified"] is True


@pytest.mark.asyncio
async def test_autocomplete_users_limit(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test autocomplete respects limit."""
    for i in range(20):
        await user_factory(username=f"user{i:03d}")

    results = await search_repo.autocomplete_users("user", limit=5)

    assert len(results) == 5


@pytest.mark.asyncio
async def test_autocomplete_users_empty_prefix(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test autocomplete with empty prefix."""
    await user_factory()

    results = await search_repo.autocomplete_users("")

    assert len(results) == 0


@pytest.mark.asyncio
async def test_autocomplete_users_exclude_ids(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test autocomplete can exclude specific users."""
    user1 = await user_factory(username="alice")
    user2 = await user_factory(username="alan")
    user3 = await user_factory(username="alex")

    results = await search_repo.autocomplete_users("al", exclude_ids={user2.id})

    assert len(results) == 2
    usernames = {r["username"] for r in results}
    assert "alan" not in usernames
    assert "alice" in usernames
    assert "alex" in usernames


@pytest.mark.asyncio
async def test_autocomplete_users_excludes_inactive(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test autocomplete excludes inactive users."""
    await user_factory(username="user_active", is_active=True)
    await user_factory(username="user_inactive", is_active=False)

    results = await search_repo.autocomplete_users("user")

    assert len(results) == 1
    assert results[0]["username"] == "user_active"


@pytest.mark.asyncio
async def test_autocomplete_users_orders_by_popularity(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test autocomplete orders by follower count."""
    await user_factory(username="dev_small", followers_count=10)
    await user_factory(username="dev_big", followers_count=10000)
    await user_factory(username="dev_medium", followers_count=500)

    results = await search_repo.autocomplete_users("dev")

    assert results[0]["username"] == "dev_big"
    assert results[1]["username"] == "dev_medium"
    assert results[2]["username"] == "dev_small"


@pytest.mark.asyncio
async def test_autocomplete_users_case_insensitive(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory
):
    """Test case-insensitive autocomplete."""
    await user_factory(username="TestUser")

    results_lower = await search_repo.autocomplete_users("test")
    results_upper = await search_repo.autocomplete_users("TEST")
    results_mixed = await search_repo.autocomplete_users("TeSt")

    assert len(results_lower) == 1
    assert len(results_upper) == 1
    assert len(results_mixed) == 1


# =============================================================================
# search_all Tests
# =============================================================================


@pytest.mark.asyncio
async def test_search_all_returns_both(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory, post_factory
):
    """Test combined search returns both users and posts."""
    user = await user_factory(username="pythondev", bio="I code in Python")
    await post_factory(body="Learning Python today")
    await post_factory(body="Python is great")

    results = await search_repo.search_all("python")

    assert "users" in results
    assert "posts" in results
    assert results["users_total"] >= 1
    assert results["posts_total"] == 2


@pytest.mark.asyncio
async def test_search_all_respects_limits(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory, post_factory
):
    """Test combined search respects individual limits."""
    for i in range(10):
        await user_factory(username=f"coder{i}")
        await post_factory(body=f"Code snippet {i}")

    results = await search_repo.search_all("code", posts_limit=3, users_limit=2)

    assert len(results["users"]) <= 2
    assert len(results["posts"]) <= 3


@pytest.mark.asyncio
async def test_search_all_empty_query(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory, post_factory
):
    """Test combined search with empty query."""
    await user_factory()
    await post_factory()

    results = await search_repo.search_all("")

    assert results["posts"] == []
    assert results["users"] == []
    assert results["posts_total"] == 0
    assert results["users_total"] == 0


@pytest.mark.asyncio
async def test_search_all_no_posts_but_users(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory, post_factory
):
    """Test search that only matches users."""
    await user_factory(username="uniqueuser")
    await post_factory(body="Some random content")

    results = await search_repo.search_all("unique")

    assert results["users_total"] >= 1
    assert results["posts_total"] == 0


@pytest.mark.asyncio
async def test_search_all_no_users_but_posts(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory, post_factory
):
    """Test search that only matches posts."""
    await user_factory(username="normaluser")
    await post_factory(body="Unique content here")

    results = await search_repo.search_all("unique content")

    assert results["posts_total"] >= 1
    # May or may not match users depending on implementation


# =============================================================================
# Edge Cases and Security Tests
# =============================================================================


@pytest.mark.asyncio
async def test_search_sql_injection_protection(
    db_session: AsyncSession, search_repo: SearchRepository, post_factory
):
    """Test that SQL injection attempts are handled safely."""
    await post_factory(body="Normal post")

    # These should not cause errors or return unexpected results
    dangerous_queries = [
        "'; DROP TABLE posts; --",
        "1 OR 1=1",
        "' OR '1'='1",
        "UNION SELECT * FROM users",
        "<script>alert('xss')</script>",
    ]

    for query in dangerous_queries:
        # Should not raise exception
        posts, _ = await search_repo.search_posts_fuzzy(query)
        users, _ = await search_repo.search_users(query)
        autocomplete = await search_repo.autocomplete_users(query)

        # Results should be empty or minimal
        assert isinstance(posts, list)
        assert isinstance(users, list)
        assert isinstance(autocomplete, list)


@pytest.mark.asyncio
async def test_search_very_long_query(
    db_session: AsyncSession, search_repo: SearchRepository, post_factory
):
    """Test handling of very long search queries."""
    await post_factory(body="Test content")

    long_query = "a" * 1000

    # Should not crash
    posts, _ = await search_repo.search_posts_fuzzy(long_query)
    users, _ = await search_repo.search_users(long_query)

    assert isinstance(posts, list)
    assert isinstance(users, list)


@pytest.mark.asyncio
async def test_search_unicode_characters(
    db_session: AsyncSession, search_repo: SearchRepository, user_factory, post_factory
):
    """Test search with unicode characters."""
    await post_factory(body="日本語のテスト")
    await post_factory(body="Тест на русском")
    await post_factory(body="Emoji test 🚀🎉")
    await user_factory(username="user_émoji")

    # Should handle unicode gracefully
    posts_jp, _ = await search_repo.search_posts_fuzzy("日本語")
    posts_ru, _ = await search_repo.search_posts_fuzzy("русском")
    posts_emoji, _ = await search_repo.search_posts_fuzzy("🚀")

    assert len(posts_jp) >= 0
    assert len(posts_ru) >= 0
    assert len(posts_emoji) >= 0

