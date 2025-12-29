"""
Tests for optimized PostRepository methods.

These tests cover the N+1 query elimination features:
- get_home_feed_optimized
- get_posts_with_like_status
- get_explore_feed_optimized
- get_trending_posts
- get_posts_by_ids_ordered
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository


# =============================================================================
# get_home_feed_optimized Tests
# =============================================================================


@pytest.mark.asyncio
async def test_home_feed_optimized_returns_followed_posts(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test that home feed returns posts from followed users."""
    post_repo = PostRepository(db_session)
    user_repo = UserRepository(db_session)

    user = await user_factory()
    followed1 = await user_factory()
    followed2 = await user_factory()
    stranger = await user_factory()

    await user_repo.follow(user.id, followed1.id)
    await user_repo.follow(user.id, followed2.id)

    # Create posts
    post1 = await post_factory(author=followed1, body="Post from followed1")
    post2 = await post_factory(author=followed2, body="Post from followed2")
    post3 = await post_factory(author=stranger, body="Post from stranger")  # Should not appear
    post4 = await post_factory(author=user, body="Own post")  # Include own posts

    following_ids = await user_repo.get_following_ids(user.id)
    following_ids.append(user.id)  # Include own posts

    posts, total = await post_repo.get_home_feed_optimized(following_ids)

    assert total == 3
    assert len(posts) == 3
    post_ids = {p.id for p in posts}
    assert post1.id in post_ids
    assert post2.id in post_ids
    assert post4.id in post_ids
    assert post3.id not in post_ids


@pytest.mark.asyncio
async def test_home_feed_optimized_empty_following(
    db_session: AsyncSession, post_factory
):
    """Test home feed with empty following list."""
    post_repo = PostRepository(db_session)

    await post_factory()
    await post_factory()

    posts, total = await post_repo.get_home_feed_optimized([])

    assert total == 0
    assert len(posts) == 0


@pytest.mark.asyncio
async def test_home_feed_optimized_pagination(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test home feed pagination works correctly."""
    post_repo = PostRepository(db_session)

    user = await user_factory()

    # Create 10 posts
    for i in range(10):
        await post_factory(author=user, body=f"Post {i}")

    # Get first page
    posts_page1, total = await post_repo.get_home_feed_optimized([user.id], skip=0, limit=3)
    assert total == 10
    assert len(posts_page1) == 3

    # Get second page
    posts_page2, total = await post_repo.get_home_feed_optimized([user.id], skip=3, limit=3)
    assert len(posts_page2) == 3

    # Ensure no overlap
    page1_ids = {p.id for p in posts_page1}
    page2_ids = {p.id for p in posts_page2}
    assert not page1_ids.intersection(page2_ids)


@pytest.mark.asyncio
async def test_home_feed_optimized_orders_by_created_at_desc(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test home feed orders by most recent first."""
    post_repo = PostRepository(db_session)

    user = await user_factory()
    older_post = await post_factory(author=user, body="Older post")
    newer_post = await post_factory(author=user, body="Newer post")

    posts, _ = await post_repo.get_home_feed_optimized([user.id])

    assert posts[0].id == newer_post.id
    assert posts[1].id == older_post.id


@pytest.mark.asyncio
async def test_home_feed_optimized_excludes_deleted(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test home feed excludes soft-deleted posts."""
    post_repo = PostRepository(db_session)

    user = await user_factory()
    visible_post = await post_factory(author=user, body="Visible")
    deleted_post = await post_factory(author=user, body="Deleted")

    # Soft delete the post
    deleted_post.deleted_at = datetime.now(timezone.utc)
    await db_session.flush()

    posts, total = await post_repo.get_home_feed_optimized([user.id])

    assert total == 1
    assert posts[0].id == visible_post.id


@pytest.mark.asyncio
async def test_home_feed_optimized_loads_author(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test that author relationship is eagerly loaded."""
    post_repo = PostRepository(db_session)

    user = await user_factory(username="postauthor")
    await post_factory(author=user)

    posts, _ = await post_repo.get_home_feed_optimized([user.id])

    assert len(posts) == 1
    assert posts[0].author is not None
    assert posts[0].author.username == "postauthor"


# =============================================================================
# get_posts_with_like_status Tests
# =============================================================================


@pytest.mark.asyncio
async def test_posts_with_like_status_all_liked(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test batch like status when all posts are liked."""
    repo = PostRepository(db_session)
    user = await user_factory()

    post1 = await post_factory()
    post2 = await post_factory()
    post3 = await post_factory()

    await repo.like_post(user.id, post1.id)
    await repo.like_post(user.id, post2.id)
    await repo.like_post(user.id, post3.id)

    status = await repo.get_posts_with_like_status([post1.id, post2.id, post3.id], user.id)

    assert status == {post1.id: True, post2.id: True, post3.id: True}


@pytest.mark.asyncio
async def test_posts_with_like_status_none_liked(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test batch like status when no posts are liked."""
    repo = PostRepository(db_session)
    user = await user_factory()

    post1 = await post_factory()
    post2 = await post_factory()

    status = await repo.get_posts_with_like_status([post1.id, post2.id], user.id)

    assert status == {post1.id: False, post2.id: False}


@pytest.mark.asyncio
async def test_posts_with_like_status_mixed(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test batch like status with mixed likes."""
    repo = PostRepository(db_session)
    user = await user_factory()

    post1 = await post_factory()
    post2 = await post_factory()
    post3 = await post_factory()

    await repo.like_post(user.id, post1.id)
    await repo.like_post(user.id, post3.id)

    status = await repo.get_posts_with_like_status([post1.id, post2.id, post3.id], user.id)

    assert status == {post1.id: True, post2.id: False, post3.id: True}


@pytest.mark.asyncio
async def test_posts_with_like_status_empty_list(
    db_session: AsyncSession, user_factory
):
    """Test batch like status with empty post list."""
    repo = PostRepository(db_session)
    user = await user_factory()

    status = await repo.get_posts_with_like_status([], user.id)

    assert status == {}


@pytest.mark.asyncio
async def test_posts_with_like_status_large_batch(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test batch like status with many posts."""
    repo = PostRepository(db_session)
    user = await user_factory()

    # Create 50 posts
    posts = []
    for i in range(50):
        post = await post_factory(body=f"Post {i}")
        posts.append(post)

    # Like every other post
    for i, post in enumerate(posts):
        if i % 2 == 0:
            await repo.like_post(user.id, post.id)

    post_ids = [p.id for p in posts]
    status = await repo.get_posts_with_like_status(post_ids, user.id)

    assert len(status) == 50
    for i, post in enumerate(posts):
        expected = i % 2 == 0
        assert status[post.id] == expected


# =============================================================================
# get_explore_feed_optimized Tests
# =============================================================================


@pytest.mark.asyncio
async def test_explore_feed_optimized_basic(
    db_session: AsyncSession, post_factory
):
    """Test basic explore feed retrieval."""
    repo = PostRepository(db_session)

    await post_factory(body="Post 1")
    await post_factory(body="Post 2")
    await post_factory(body="Post 3")

    posts, total = await repo.get_explore_feed_optimized()

    assert total == 3
    assert len(posts) == 3


@pytest.mark.asyncio
async def test_explore_feed_optimized_pagination(
    db_session: AsyncSession, post_factory
):
    """Test explore feed pagination."""
    repo = PostRepository(db_session)

    for i in range(15):
        await post_factory(body=f"Post {i}")

    posts_page1, total = await repo.get_explore_feed_optimized(skip=0, limit=5)
    posts_page2, _ = await repo.get_explore_feed_optimized(skip=5, limit=5)
    posts_page3, _ = await repo.get_explore_feed_optimized(skip=10, limit=5)

    assert total == 15
    assert len(posts_page1) == 5
    assert len(posts_page2) == 5
    assert len(posts_page3) == 5

    # All pages should have unique posts
    all_ids = [p.id for p in posts_page1 + posts_page2 + posts_page3]
    assert len(set(all_ids)) == 15


@pytest.mark.asyncio
async def test_explore_feed_optimized_engagement_scoring(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test that posts are sorted by engagement score."""
    repo = PostRepository(db_session)

    # Create posts with different engagement
    low_engagement = await post_factory(body="Low engagement")
    high_engagement = await post_factory(body="High engagement")
    medium_engagement = await post_factory(body="Medium engagement")

    # Set engagement counts
    high_engagement.likes_count = 100
    high_engagement.comments_count = 50
    await db_session.flush()

    medium_engagement.likes_count = 20
    medium_engagement.comments_count = 10
    await db_session.flush()

    low_engagement.likes_count = 1
    low_engagement.comments_count = 0
    await db_session.flush()

    posts, _ = await repo.get_explore_feed_optimized()

    # High engagement should come first
    assert posts[0].id == high_engagement.id
    assert posts[1].id == medium_engagement.id
    assert posts[2].id == low_engagement.id


@pytest.mark.asyncio
async def test_explore_feed_optimized_excludes_deleted(
    db_session: AsyncSession, post_factory
):
    """Test explore feed excludes deleted posts."""
    repo = PostRepository(db_session)

    visible = await post_factory(body="Visible")
    deleted = await post_factory(body="Deleted")

    deleted.deleted_at = datetime.now(timezone.utc)
    await db_session.flush()

    posts, total = await repo.get_explore_feed_optimized()

    assert total == 1
    assert posts[0].id == visible.id


@pytest.mark.asyncio
async def test_explore_feed_optimized_recency_bonus(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test that recent posts get recency bonus in scoring."""
    repo = PostRepository(db_session)

    # Create an old post with high engagement
    old_post = await post_factory(body="Old high engagement")
    old_post.likes_count = 50
    old_post.comments_count = 20
    # Manually set old created_at
    old_post.created_at = datetime.now(timezone.utc) - timedelta(hours=48)
    await db_session.flush()

    # Create a newer post with moderate engagement
    new_post = await post_factory(body="New moderate engagement")
    new_post.likes_count = 30
    new_post.comments_count = 10
    await db_session.flush()

    # Get explore feed with 24-hour recency window
    posts, _ = await repo.get_explore_feed_optimized(hours=24)

    # Both should be returned
    assert len(posts) == 2


@pytest.mark.asyncio
async def test_explore_feed_optimized_loads_author(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test that author is eagerly loaded."""
    repo = PostRepository(db_session)

    user = await user_factory(username="explorer")
    await post_factory(author=user)

    posts, _ = await repo.get_explore_feed_optimized()

    assert posts[0].author is not None
    assert posts[0].author.username == "explorer"


# =============================================================================
# get_trending_posts Tests
# =============================================================================


@pytest.mark.asyncio
async def test_trending_posts_basic(
    db_session: AsyncSession, post_factory
):
    """Test basic trending posts retrieval."""
    repo = PostRepository(db_session)

    post1 = await post_factory(body="Trending 1")
    post1.likes_count = 100
    await db_session.flush()

    post2 = await post_factory(body="Trending 2")
    post2.likes_count = 50
    await db_session.flush()

    posts = await repo.get_trending_posts(hours=24, limit=10)

    assert len(posts) == 2
    # Higher engagement first
    assert posts[0].id == post1.id


@pytest.mark.asyncio
async def test_trending_posts_respects_time_window(
    db_session: AsyncSession, post_factory
):
    """Test trending posts only includes posts from time window."""
    repo = PostRepository(db_session)

    # Recent post
    recent = await post_factory(body="Recent")
    recent.likes_count = 10
    await db_session.flush()

    # Old post (outside 6-hour window)
    old = await post_factory(body="Old")
    old.likes_count = 100
    old.created_at = datetime.now(timezone.utc) - timedelta(hours=12)
    await db_session.flush()

    posts = await repo.get_trending_posts(hours=6, limit=10)

    assert len(posts) == 1
    assert posts[0].id == recent.id


@pytest.mark.asyncio
async def test_trending_posts_limit(
    db_session: AsyncSession, post_factory
):
    """Test trending posts respects limit."""
    repo = PostRepository(db_session)

    for i in range(10):
        post = await post_factory(body=f"Post {i}")
        post.likes_count = i * 10
        await db_session.flush()

    posts = await repo.get_trending_posts(hours=24, limit=5)

    assert len(posts) == 5


@pytest.mark.asyncio
async def test_trending_posts_comments_weight(
    db_session: AsyncSession, post_factory
):
    """Test that comments are weighted higher than likes."""
    repo = PostRepository(db_session)

    # Post with many likes but no comments
    likes_post = await post_factory(body="Many likes")
    likes_post.likes_count = 20
    likes_post.comments_count = 0
    await db_session.flush()

    # Post with fewer likes but more comments (comments * 2)
    comments_post = await post_factory(body="Many comments")
    comments_post.likes_count = 5
    comments_post.comments_count = 15  # 5 + 15*2 = 35 > 20
    await db_session.flush()

    posts = await repo.get_trending_posts(hours=24, limit=10)

    # Comments post should rank higher
    assert posts[0].id == comments_post.id


@pytest.mark.asyncio
async def test_trending_posts_excludes_deleted(
    db_session: AsyncSession, post_factory
):
    """Test trending posts excludes deleted posts."""
    repo = PostRepository(db_session)

    visible = await post_factory(body="Visible")
    visible.likes_count = 50
    await db_session.flush()

    deleted = await post_factory(body="Deleted")
    deleted.likes_count = 100
    deleted.deleted_at = datetime.now(timezone.utc)
    await db_session.flush()

    posts = await repo.get_trending_posts(hours=24)

    assert len(posts) == 1
    assert posts[0].id == visible.id


# =============================================================================
# get_posts_by_ids_ordered Tests
# =============================================================================


@pytest.mark.asyncio
async def test_posts_by_ids_ordered_maintains_order(
    db_session: AsyncSession, post_factory
):
    """Test that posts are returned in the order of input IDs."""
    repo = PostRepository(db_session)

    post1 = await post_factory(body="First")
    post2 = await post_factory(body="Second")
    post3 = await post_factory(body="Third")

    # Request in specific order
    requested_order = [post3.id, post1.id, post2.id]
    posts = await repo.get_posts_by_ids_ordered(requested_order)

    assert len(posts) == 3
    assert posts[0].id == post3.id
    assert posts[1].id == post1.id
    assert posts[2].id == post2.id


@pytest.mark.asyncio
async def test_posts_by_ids_ordered_empty_list(
    db_session: AsyncSession
):
    """Test with empty ID list."""
    repo = PostRepository(db_session)

    posts = await repo.get_posts_by_ids_ordered([])

    assert posts == []


@pytest.mark.asyncio
async def test_posts_by_ids_ordered_missing_ids(
    db_session: AsyncSession, post_factory
):
    """Test graceful handling of missing IDs."""
    repo = PostRepository(db_session)

    post1 = await post_factory()
    post2 = await post_factory()

    # Include a non-existent ID
    posts = await repo.get_posts_by_ids_ordered([post1.id, 99999, post2.id])

    # Should return only existing posts in order
    assert len(posts) == 2
    assert posts[0].id == post1.id
    assert posts[1].id == post2.id


@pytest.mark.asyncio
async def test_posts_by_ids_ordered_excludes_deleted(
    db_session: AsyncSession, post_factory
):
    """Test that deleted posts are excluded."""
    repo = PostRepository(db_session)

    visible = await post_factory()
    deleted = await post_factory()
    deleted.deleted_at = datetime.now(timezone.utc)
    await db_session.flush()

    posts = await repo.get_posts_by_ids_ordered([visible.id, deleted.id])

    assert len(posts) == 1
    assert posts[0].id == visible.id


@pytest.mark.asyncio
async def test_posts_by_ids_ordered_loads_author(
    db_session: AsyncSession, user_factory, post_factory
):
    """Test that author is eagerly loaded."""
    repo = PostRepository(db_session)

    user = await user_factory(username="orderedauthor")
    post = await post_factory(author=user)

    posts = await repo.get_posts_by_ids_ordered([post.id])

    assert posts[0].author is not None
    assert posts[0].author.username == "orderedauthor"


@pytest.mark.asyncio
async def test_posts_by_ids_ordered_duplicate_ids(
    db_session: AsyncSession, post_factory
):
    """Test handling of duplicate IDs in request."""
    repo = PostRepository(db_session)

    post = await post_factory()

    # Request same ID multiple times
    posts = await repo.get_posts_by_ids_ordered([post.id, post.id, post.id])

    # Should return the post for each occurrence
    assert len(posts) == 3
    assert all(p.id == post.id for p in posts)

