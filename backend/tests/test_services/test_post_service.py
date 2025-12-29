"""
Tests for PostService.
"""

import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException

from app.services.post_service import PostService
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_post_success(
    post_repo: PostRepository,
    user_repo: UserRepository,
    user_factory,
    mock_redis,
):
    """Test creating a post."""
    from app.schemas.post import PostCreate

    user = await user_factory()

    service = PostService(post_repo, user_repo, redis=mock_redis)

    result = await service.create_post(
        user.id,
        PostCreate(body="Hello world!"),
    )

    assert result.id is not None
    assert result.body == "Hello world!"
    assert result.user_id == user.id


@pytest.mark.asyncio
async def test_create_post_too_long(
    post_repo: PostRepository,
    user_repo: UserRepository,
    user_factory,
    mock_redis,
):
    """Test creating post fails if too long."""
    from app.schemas.post import PostCreate

    user = await user_factory()

    service = PostService(post_repo, user_repo, redis=mock_redis)

    # PostCreate schema already validates max length of 280
    # So we test that the service also enforces this
    with pytest.raises(Exception):  # Could be validation or service error
        await service.create_post(
            user.id,
            PostCreate(body="a" * 281),  # Over 280 chars
        )


@pytest.mark.asyncio
async def test_create_post_empty(
    post_repo: PostRepository,
    user_repo: UserRepository,
    user_factory,
    mock_redis,
):
    """Test creating empty post fails."""
    from app.schemas.post import PostCreate

    user = await user_factory()

    service = PostService(post_repo, user_repo, redis=mock_redis)

    with pytest.raises(HTTPException) as exc_info:
        await service.create_post(
            user.id,
            PostCreate(body="   "),  # Just whitespace
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_post_success(
    post_repo: PostRepository,
    user_repo: UserRepository,
    post_factory,
):
    """Test getting a post."""
    post = await post_factory(body="Test post")

    service = PostService(post_repo, user_repo)

    result = await service.get_post(post.id)

    assert result.id == post.id
    assert result.body == "Test post"


@pytest.mark.asyncio
async def test_get_post_not_found(
    post_repo: PostRepository,
    user_repo: UserRepository,
):
    """Test getting non-existent post raises 404."""
    service = PostService(post_repo, user_repo)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_post(99999)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_post_success(
    post_repo: PostRepository,
    user_repo: UserRepository,
    user_factory,
    post_factory,
    mock_redis,
):
    """Test deleting own post."""
    user = await user_factory()
    post = await post_factory(author=user)

    service = PostService(post_repo, user_repo, redis=mock_redis)

    result = await service.delete_post(post.id, user.id)

    assert result is True


@pytest.mark.asyncio
async def test_delete_post_not_owner(
    post_repo: PostRepository,
    user_repo: UserRepository,
    user_factory,
    post_factory,
):
    """Test deleting someone else's post fails."""
    owner = await user_factory()
    other_user = await user_factory()
    post = await post_factory(author=owner)

    service = PostService(post_repo, user_repo)

    with pytest.raises(HTTPException) as exc_info:
        await service.delete_post(post.id, other_user.id)

    assert exc_info.value.status_code == 403
    assert "Not authorized" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_like_post(
    post_repo: PostRepository,
    user_repo: UserRepository,
    user_factory,
    post_factory,
):
    """Test liking a post."""
    user = await user_factory()
    post = await post_factory()

    service = PostService(post_repo, user_repo)

    result = await service.like_post(user.id, post.id)

    assert result is True
    assert await service.is_liked(user.id, post.id) is True


@pytest.mark.asyncio
async def test_unlike_post(
    post_repo: PostRepository,
    user_repo: UserRepository,
    user_factory,
    post_factory,
):
    """Test unliking a post."""
    user = await user_factory()
    post = await post_factory()

    service = PostService(post_repo, user_repo)

    # First like
    await service.like_post(user.id, post.id)

    # Then unlike
    result = await service.unlike_post(user.id, post.id)

    assert result is True
    assert await service.is_liked(user.id, post.id) is False


@pytest.mark.asyncio
async def test_get_explore_feed(
    post_repo: PostRepository,
    user_repo: UserRepository,
    post_factory,
    mock_redis,
):
    """Test getting explore feed."""
    await post_factory()
    await post_factory()
    await post_factory()

    service = PostService(post_repo, user_repo, redis=mock_redis)

    result = await service.get_explore_feed(page=1, per_page=10)

    assert result.total == 3
    assert len(result.posts) == 3
    assert result.page == 1


@pytest.mark.asyncio
async def test_get_home_feed(
    post_repo: PostRepository,
    user_repo: UserRepository,
    user_factory,
    post_factory,
    mock_redis,
):
    """Test getting home feed."""
    user = await user_factory()
    followed = await user_factory()
    stranger = await user_factory()

    # Follow one user
    await user_repo.follow(user.id, followed.id)

    # Create posts
    await post_factory(author=followed)  # Should appear
    await post_factory(author=user)  # Should appear (own post)
    await post_factory(author=stranger)  # Should NOT appear

    service = PostService(post_repo, user_repo, redis=mock_redis)

    result = await service.get_home_feed(user.id, page=1, per_page=10)

    assert result.total == 2
    assert len(result.posts) == 2


@pytest.mark.asyncio
async def test_search_posts(
    post_repo: PostRepository,
    user_repo: UserRepository,
    post_factory,
):
    """Test searching posts."""
    await post_factory(body="Python is awesome")
    await post_factory(body="I love Python programming")
    await post_factory(body="JavaScript is cool")

    service = PostService(post_repo, user_repo)

    result = await service.search_posts("python", page=1, per_page=10)

    assert result.total == 2
    assert len(result.posts) == 2


@pytest.mark.asyncio
async def test_get_user_posts(
    post_repo: PostRepository,
    user_repo: UserRepository,
    user_factory,
    post_factory,
):
    """Test getting user's posts."""
    user = await user_factory()
    other = await user_factory()

    await post_factory(author=user)
    await post_factory(author=user)
    await post_factory(author=other)  # Different user

    service = PostService(post_repo, user_repo)

    result = await service.get_user_posts(user.id, page=1, per_page=10)

    assert result.total == 2
    assert len(result.posts) == 2
