"""
Tests for UserService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from app.services.user_service import UserService
from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_get_user_by_id_success(user_repo: UserRepository, user_factory):
    """Test getting user by ID."""
    user = await user_factory(username="findme")

    service = UserService(user_repo)

    result = await service.get_user_by_id(user.id)

    assert result.id == user.id
    assert result.username == "findme"


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(user_repo: UserRepository):
    """Test getting non-existent user raises 404."""
    service = UserService(user_repo)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_user_by_id(99999)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_user_by_username_success(user_repo: UserRepository, user_factory):
    """Test getting user by username."""
    user = await user_factory(username="findbyname")

    service = UserService(user_repo)

    result = await service.get_user_by_username("findbyname")

    assert result.id == user.id


@pytest.mark.asyncio
async def test_update_profile(user_repo: UserRepository, user_factory):
    """Test updating user profile."""
    from app.schemas.user import UserUpdate

    user = await user_factory(display_name="Old Name")

    service = UserService(user_repo)

    result = await service.update_profile(
        user.id,
        UserUpdate(display_name="New Name", bio="Updated bio"),
    )

    assert result.display_name == "New Name"
    assert result.bio == "Updated bio"


@pytest.mark.asyncio
async def test_update_profile_duplicate_username(
    user_repo: UserRepository, user_factory
):
    """Test updating profile fails if username already taken."""
    from app.schemas.user import UserUpdate

    await user_factory(username="taken")
    user = await user_factory(username="original")

    service = UserService(user_repo)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_profile(user.id, UserUpdate(username="taken"))

    assert exc_info.value.status_code == 400
    assert "Username already taken" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_follow_user_success(user_repo: UserRepository, user_factory):
    """Test following a user."""
    user1 = await user_factory()
    user2 = await user_factory()

    service = UserService(user_repo)

    result = await service.follow_user(user1.id, user2.id)

    assert result is True
    assert await user_repo.is_following(user1.id, user2.id) is True


@pytest.mark.asyncio
async def test_follow_self_fails(user_repo: UserRepository, user_factory):
    """Test following yourself fails."""
    user = await user_factory()

    service = UserService(user_repo)

    with pytest.raises(HTTPException) as exc_info:
        await service.follow_user(user.id, user.id)

    assert exc_info.value.status_code == 400
    assert "Cannot follow yourself" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_follow_nonexistent_user(user_repo: UserRepository, user_factory):
    """Test following non-existent user fails."""
    user = await user_factory()

    service = UserService(user_repo)

    with pytest.raises(HTTPException) as exc_info:
        await service.follow_user(user.id, 99999)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_unfollow_user(user_repo: UserRepository, user_factory):
    """Test unfollowing a user."""
    user1 = await user_factory()
    user2 = await user_factory()

    # First follow
    await user_repo.follow(user1.id, user2.id)

    service = UserService(user_repo)

    result = await service.unfollow_user(user1.id, user2.id)

    assert result is True
    assert await user_repo.is_following(user1.id, user2.id) is False


@pytest.mark.asyncio
async def test_is_following(user_repo: UserRepository, user_factory):
    """Test checking follow status."""
    user1 = await user_factory()
    user2 = await user_factory()

    service = UserService(user_repo)

    # Not following initially
    assert await service.is_following(user1.id, user2.id) is False

    # After follow
    await user_repo.follow(user1.id, user2.id)
    assert await service.is_following(user1.id, user2.id) is True


@pytest.mark.asyncio
async def test_get_followers(user_repo: UserRepository, user_factory):
    """Test getting followers list."""
    user = await user_factory()
    follower1 = await user_factory()
    follower2 = await user_factory()

    await user_repo.follow(follower1.id, user.id)
    await user_repo.follow(follower2.id, user.id)

    service = UserService(user_repo)

    result = await service.get_followers(user.id, page=1, per_page=10)

    assert result.total == 2
    assert len(result.items) == 2
    assert result.page == 1


@pytest.mark.asyncio
async def test_get_following(user_repo: UserRepository, user_factory):
    """Test getting following list."""
    user = await user_factory()
    followed1 = await user_factory()
    followed2 = await user_factory()

    await user_repo.follow(user.id, followed1.id)
    await user_repo.follow(user.id, followed2.id)

    service = UserService(user_repo)

    result = await service.get_following(user.id, page=1, per_page=10)

    assert result.total == 2
    assert len(result.items) == 2


@pytest.mark.asyncio
async def test_search_users(user_repo: UserRepository, user_factory):
    """Test searching users."""
    await user_factory(username="alice")
    await user_factory(username="bob")
    await user_factory(username="alicia")

    service = UserService(user_repo)

    result = await service.search_users("ali", page=1, per_page=10)

    assert result.total == 2
    assert len(result.items) == 2
