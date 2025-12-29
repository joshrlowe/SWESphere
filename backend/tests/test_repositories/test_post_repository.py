"""
Tests for PostRepository.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_post(db_session: AsyncSession, user_factory):
    """Test creating a new post."""
    repo = PostRepository(db_session)
    user = await user_factory()
    
    post = await repo.create(
        user_id=user.id,
        body="Hello world!",
    )
    
    assert post.id is not None
    assert post.body == "Hello world!"
    assert post.user_id == user.id


@pytest.mark.asyncio
async def test_get_with_author(db_session: AsyncSession, post_factory):
    """Test getting post with author loaded."""
    repo = PostRepository(db_session)
    post = await post_factory()
    
    found = await repo.get_with_author(post.id)
    
    assert found is not None
    assert found.author is not None
    assert found.author.id == post.user_id


@pytest.mark.asyncio
async def test_get_user_posts(db_session: AsyncSession, user_factory, post_factory):
    """Test getting all posts by a user."""
    repo = PostRepository(db_session)
    user = await user_factory()
    
    await post_factory(author=user)
    await post_factory(author=user)
    await post_factory()  # Different author
    
    posts, total = await repo.get_user_posts(user.id)
    
    assert total == 2
    assert len(posts) == 2


@pytest.mark.asyncio
async def test_like_post(db_session: AsyncSession, user_factory, post_factory):
    """Test liking a post."""
    repo = PostRepository(db_session)
    user = await user_factory()
    post = await post_factory()
    
    result = await repo.like_post(user.id, post.id)
    
    assert result is True
    assert await repo.is_liked_by(post.id, user.id) is True


@pytest.mark.asyncio
async def test_like_post_twice_fails(db_session: AsyncSession, user_factory, post_factory):
    """Test that liking twice fails."""
    repo = PostRepository(db_session)
    user = await user_factory()
    post = await post_factory()
    
    await repo.like_post(user.id, post.id)
    result = await repo.like_post(user.id, post.id)
    
    assert result is False


@pytest.mark.asyncio
async def test_unlike_post(db_session: AsyncSession, user_factory, post_factory):
    """Test unliking a post."""
    repo = PostRepository(db_session)
    user = await user_factory()
    post = await post_factory()
    
    await repo.like_post(user.id, post.id)
    result = await repo.unlike_post(user.id, post.id)
    
    assert result is True
    assert await repo.is_liked_by(post.id, user.id) is False


@pytest.mark.asyncio
async def test_get_liked_post_ids(db_session: AsyncSession, user_factory, post_factory):
    """Test batch checking liked posts."""
    repo = PostRepository(db_session)
    user = await user_factory()
    post1 = await post_factory()
    post2 = await post_factory()
    post3 = await post_factory()
    
    await repo.like_post(user.id, post1.id)
    await repo.like_post(user.id, post3.id)
    
    liked = await repo.get_liked_post_ids(user.id, [post1.id, post2.id, post3.id])
    
    assert liked == {post1.id, post3.id}


@pytest.mark.asyncio
async def test_get_explore_feed(db_session: AsyncSession, post_factory):
    """Test getting explore feed."""
    repo = PostRepository(db_session)
    
    await post_factory()
    await post_factory()
    await post_factory()
    
    posts, total = await repo.get_explore_feed(limit=2)
    
    assert total == 3
    assert len(posts) == 2


@pytest.mark.asyncio
async def test_get_home_feed(db_session: AsyncSession, user_factory, post_factory):
    """Test getting home feed with followed users."""
    post_repo = PostRepository(db_session)
    user_repo = UserRepository(db_session)
    
    user = await user_factory()
    followed = await user_factory()
    stranger = await user_factory()
    
    await user_repo.follow(user.id, followed.id)
    
    await post_factory(author=followed)
    await post_factory(author=user)
    await post_factory(author=stranger)  # Should not appear
    
    following_ids = await user_repo.get_following_ids(user.id)
    posts, total = await post_repo.get_home_feed(user.id, following_ids)
    
    assert total == 2
    assert len(posts) == 2


@pytest.mark.asyncio
async def test_search_posts(db_session: AsyncSession, post_factory):
    """Test searching posts by content."""
    repo = PostRepository(db_session)
    
    await post_factory(body="Python is awesome")
    await post_factory(body="I love Python programming")
    await post_factory(body="JavaScript is cool")
    
    posts, total = await repo.search_posts("python")
    
    assert total == 2
    assert len(posts) == 2


@pytest.mark.asyncio
async def test_get_replies(db_session: AsyncSession, user_factory, post_factory):
    """Test getting replies to a post."""
    repo = PostRepository(db_session)
    user = await user_factory()
    parent = await post_factory(author=user)
    
    await post_factory(author=user, reply_to_id=parent.id)
    await post_factory(author=user, reply_to_id=parent.id)
    
    replies, total = await repo.get_replies(parent.id)
    
    assert total == 2
    assert len(replies) == 2

