"""Notification routes."""

from typing import Any

from fastapi import APIRouter, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.dependencies import NotificationSvc

router = APIRouter()


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: int
    type: str
    read: bool
    data: dict[str, Any]
    actor_id: int | None
    created_at: Any

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    """Unread count response."""

    count: int


@router.get(
    "/",
    response_model=list[NotificationResponse],
    summary="Get notifications",
)
async def get_notifications(
    current_user: CurrentUser,
    notification_service: NotificationSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
) -> list[NotificationResponse]:
    """
    Get the current user's notifications.
    """
    notifications = await notification_service.get_user_notifications(
        current_user.id,
        skip=skip,
        limit=limit,
        unread_only=unread_only,
    )
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
)
async def get_unread_count(
    current_user: CurrentUser,
    notification_service: NotificationSvc,
) -> UnreadCountResponse:
    """
    Get the count of unread notifications.
    """
    count = await notification_service.get_unread_count(current_user.id)
    return UnreadCountResponse(count=count)


@router.post(
    "/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark notification as read",
)
async def mark_as_read(
    notification_id: int,
    current_user: CurrentUser,
    notification_service: NotificationSvc,
) -> None:
    """
    Mark a specific notification as read.
    """
    await notification_service.mark_as_read(notification_id, current_user.id)


@router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all notifications as read",
)
async def mark_all_as_read(
    current_user: CurrentUser,
    notification_service: NotificationSvc,
) -> None:
    """
    Mark all notifications as read for the current user.
    """
    await notification_service.mark_all_as_read(current_user.id)


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a notification",
)
async def delete_notification(
    notification_id: int,
    current_user: CurrentUser,
    notification_service: NotificationSvc,
) -> None:
    """
    Delete a notification.
    """
    await notification_service.delete_notification(notification_id, current_user.id)

