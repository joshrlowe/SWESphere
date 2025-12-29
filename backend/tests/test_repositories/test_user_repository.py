"""
Tests for UserRepository.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """Test creating a new user."""
    repo = UserRepository(db_session)
    
    user = await repo.create(
        username="newuser",
        email="new@example.com",
        password_hash="hashed",
    )
    
    assert user.id is not None
    assert user.username == "newuser"
    assert user.email == "new@example.com"


@pytest.mark.asyncio
async def test_get_by_username(db_session: AsyncSession, user_factory):
    """Test finding user by username."""
    repo = UserRepository(db_session)
    created_user = await user_factory(username="findme")
    
    found = await repo.get_by_username("findme")
    
    assert found is not None
    assert found.id == created_user.id


@pytest.mark.asyncio
async def test_get_by_username_case_insensitive(db_session: AsyncSession, user_factory):
    """Test username lookup is case-insensitive."""
    repo = UserRepository(db_session)
    await user_factory(username="TestUser")
    
    found = await repo.get_by_username("testuser")
    
    assert found is not None
    assert found.username == "TestUser"


@pytest.mark.asyncio
async def test_get_by_email(db_session: AsyncSession, user_factory):
    """Test finding user by email."""
    repo = UserRepository(db_session)
    created_user = await user_factory(email="find@example.com")
    
    found = await repo.get_by_email("find@example.com")
    
    assert found is not None
    assert found.id == created_user.id


@pytest.mark.asyncio
async def test_follow_user(db_session: AsyncSession, user_factory):
    """Test following another user."""
    repo = UserRepository(db_session)
    user1 = await user_factory()
    user2 = await user_factory()
    
    result = await repo.follow(user1.id, user2.id)
    
    assert result is True
    assert await repo.is_following(user1.id, user2.id) is True


@pytest.mark.asyncio
async def test_follow_self_fails(db_session: AsyncSession, user_factory):
    """Test that following yourself fails."""
    repo = UserRepository(db_session)
    user = await user_factory()
    
    result = await repo.follow(user.id, user.id)
    
    assert result is False


@pytest.mark.asyncio
async def test_follow_twice_fails(db_session: AsyncSession, user_factory):
    """Test that following twice fails."""
    repo = UserRepository(db_session)
    user1 = await user_factory()
    user2 = await user_factory()
    
    await repo.follow(user1.id, user2.id)
    result = await repo.follow(user1.id, user2.id)
    
    assert result is False


@pytest.mark.asyncio
async def test_unfollow_user(db_session: AsyncSession, user_factory):
    """Test unfollowing a user."""
    repo = UserRepository(db_session)
    user1 = await user_factory()
    user2 = await user_factory()
    
    await repo.follow(user1.id, user2.id)
    result = await repo.unfollow(user1.id, user2.id)
    
    assert result is True
    assert await repo.is_following(user1.id, user2.id) is False


@pytest.mark.asyncio
async def test_get_followers(db_session: AsyncSession, user_factory):
    """Test getting followers list."""
    repo = UserRepository(db_session)
    user = await user_factory()
    follower1 = await user_factory()
    follower2 = await user_factory()
    
    await repo.follow(follower1.id, user.id)
    await repo.follow(follower2.id, user.id)
    
    followers = await repo.get_followers(user.id)
    
    assert len(followers) == 2


@pytest.mark.asyncio
async def test_get_following(db_session: AsyncSession, user_factory):
    """Test getting following list."""
    repo = UserRepository(db_session)
    user = await user_factory()
    followed1 = await user_factory()
    followed2 = await user_factory()
    
    await repo.follow(user.id, followed1.id)
    await repo.follow(user.id, followed2.id)
    
    following = await repo.get_following(user.id)
    
    assert len(following) == 2


@pytest.mark.asyncio
async def test_search_users(db_session: AsyncSession, user_factory):
    """Test searching users by username."""
    repo = UserRepository(db_session)
    await user_factory(username="alice")
    await user_factory(username="bob")
    await user_factory(username="alicia")
    
    results, total = await repo.search_users("ali")
    
    assert total == 2
    assert len(results) == 2

