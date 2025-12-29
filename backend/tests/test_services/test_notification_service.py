"""
Tests for NotificationService.
"""

import pytest
from unittest.mock import AsyncMock

from app.services.notification_service import NotificationService
from app.models.notification import NotificationType


@pytest.mark.asyncio
async def test_create_notification(db_session, mock_redis, user_factory):
    """Test creating a notification."""
    user = await user_factory()
    actor = await user_factory()

    service = NotificationService(db_session, mock_redis)

    result = await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.NEW_FOLLOWER,
        data={"follower_username": actor.username},
        actor_id=actor.id,
    )

    assert result is not None
    assert result.user_id == user.id
    assert result.actor_id == actor.id
    assert result.type == NotificationType.NEW_FOLLOWER

    # Should publish to Redis
    mock_redis.publish.assert_called()


@pytest.mark.asyncio
async def test_create_notification_prevents_self_notification(
    db_session,
    mock_redis,
    user_factory,
):
    """Test that self-notifications are prevented."""
    user = await user_factory()

    service = NotificationService(db_session, mock_redis)

    result = await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.POST_LIKED,
        data={"post_id": 1},
        actor_id=user.id,  # Same as user_id
    )

    assert result is None  # Should return None, not create notification


@pytest.mark.asyncio
async def test_notify_new_follower(db_session, mock_redis, user_factory):
    """Test new follower notification factory."""
    user = await user_factory()
    follower = await user_factory(username="follower_user")

    service = NotificationService(db_session, mock_redis)

    result = await service.notify_new_follower(
        user_id=user.id,
        follower_id=follower.id,
        follower_username="follower_user",
    )

    assert result is not None
    assert result.type == NotificationType.NEW_FOLLOWER
    assert result.data["follower_username"] == "follower_user"


@pytest.mark.asyncio
async def test_notify_post_liked(db_session, mock_redis, user_factory):
    """Test post liked notification factory."""
    user = await user_factory()
    liker = await user_factory(username="liker_user")

    service = NotificationService(db_session, mock_redis)

    result = await service.notify_post_liked(
        user_id=user.id,
        liker_id=liker.id,
        liker_username="liker_user",
        post_id=123,
    )

    assert result is not None
    assert result.type == NotificationType.POST_LIKED
    assert result.data["post_id"] == 123


@pytest.mark.asyncio
async def test_get_notifications(db_session, mock_redis, user_factory):
    """Test getting paginated notifications."""
    user = await user_factory()
    actor = await user_factory()

    service = NotificationService(db_session, mock_redis)

    # Create some notifications
    await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.NEW_FOLLOWER,
        data={},
        actor_id=actor.id,
    )
    await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.POST_LIKED,
        data={},
        actor_id=actor.id,
    )

    result = await service.get_notifications(user.id, page=1, per_page=10)

    assert result.total == 2
    assert len(result.items) == 2
    assert result.unread_count == 2


@pytest.mark.asyncio
async def test_get_notifications_unread_only(db_session, mock_redis, user_factory):
    """Test getting only unread notifications."""
    user = await user_factory()
    actor = await user_factory()

    service = NotificationService(db_session, mock_redis)

    # Create notifications
    notif1 = await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.NEW_FOLLOWER,
        data={},
        actor_id=actor.id,
    )
    await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.POST_LIKED,
        data={},
        actor_id=actor.id,
    )

    # Mark one as read
    await service.mark_as_read(notif1.id, user.id)

    result = await service.get_notifications(
        user.id, page=1, per_page=10, unread_only=True
    )

    assert result.total == 1
    assert len(result.items) == 1


@pytest.mark.asyncio
async def test_get_unread_count(db_session, mock_redis, user_factory):
    """Test getting unread count."""
    user = await user_factory()
    actor = await user_factory()

    # Reset mock to not return cached value
    mock_redis.get = AsyncMock(return_value=None)

    service = NotificationService(db_session, mock_redis)

    # Create unread notifications
    await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.NEW_FOLLOWER,
        data={},
        actor_id=actor.id,
    )
    await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.POST_LIKED,
        data={},
        actor_id=actor.id,
    )

    count = await service.get_unread_count(user.id)

    assert count == 2


@pytest.mark.asyncio
async def test_mark_as_read(db_session, mock_redis, user_factory):
    """Test marking notification as read."""
    user = await user_factory()
    actor = await user_factory()

    service = NotificationService(db_session, mock_redis)

    notif = await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.NEW_FOLLOWER,
        data={},
        actor_id=actor.id,
    )

    result = await service.mark_as_read(notif.id, user.id)

    assert result is True


@pytest.mark.asyncio
async def test_mark_as_read_wrong_user(db_session, mock_redis, user_factory):
    """Test marking other user's notification as read fails."""
    user = await user_factory()
    other = await user_factory()
    actor = await user_factory()

    service = NotificationService(db_session, mock_redis)

    notif = await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.NEW_FOLLOWER,
        data={},
        actor_id=actor.id,
    )

    # Try to mark as read by different user
    result = await service.mark_as_read(notif.id, other.id)

    assert result is False


@pytest.mark.asyncio
async def test_mark_all_as_read(db_session, mock_redis, user_factory):
    """Test marking all notifications as read."""
    user = await user_factory()
    actor = await user_factory()

    service = NotificationService(db_session, mock_redis)

    # Create multiple notifications
    await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.NEW_FOLLOWER,
        data={},
        actor_id=actor.id,
    )
    await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.POST_LIKED,
        data={},
        actor_id=actor.id,
    )

    count = await service.mark_all_as_read(user.id)

    assert count == 2


@pytest.mark.asyncio
async def test_delete_notification(db_session, mock_redis, user_factory):
    """Test deleting a notification."""
    user = await user_factory()
    actor = await user_factory()

    service = NotificationService(db_session, mock_redis)

    notif = await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.NEW_FOLLOWER,
        data={},
        actor_id=actor.id,
    )

    result = await service.delete_notification(notif.id, user.id)

    assert result is True


@pytest.mark.asyncio
async def test_delete_notification_wrong_user(db_session, mock_redis, user_factory):
    """Test deleting other user's notification fails."""
    user = await user_factory()
    other = await user_factory()
    actor = await user_factory()

    service = NotificationService(db_session, mock_redis)

    notif = await service.create_notification(
        user_id=user.id,
        notification_type=NotificationType.NEW_FOLLOWER,
        data={},
        actor_id=actor.id,
    )

    result = await service.delete_notification(notif.id, other.id)

    assert result is False
