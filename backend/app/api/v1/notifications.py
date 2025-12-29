"""
Notification routes.

Endpoints for managing user notifications.
"""

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser
from app.dependencies import NotificationSvc
from app.schemas.common import MessageResponse
from app.schemas.notification import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)

router = APIRouter()


# =============================================================================
# Notification List
# =============================================================================


@router.get(
    "/",
    response_model=NotificationListResponse,
    summary="Get notifications",
    responses={
        200: {"description": "List of notifications"},
        401: {"description": "Not authenticated"},
    },
)
async def get_notifications(
    current_user: CurrentUser,
    notification_service: NotificationSvc,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Notifications per page"),
    unread_only: bool = Query(False, description="Show only unread notifications"),
) -> NotificationListResponse:
    """
    Get the current user's notifications.

    - **page**: Page number (1-indexed)
    - **per_page**: Number of notifications per page
    - **unread_only**: If true, only return unread notifications

    Notifications are ordered by most recent first.
    """
    result = await notification_service.get_notifications(
        current_user.id,
        page=page,
        per_page=per_page,
        unread_only=unread_only,
    )
    return NotificationListResponse.create(
        notifications=result.notifications,
        total=result.total,
        page=page,
        per_page=per_page,
        unread_count=result.unread_count,
    )


# =============================================================================
# Unread Count
# =============================================================================


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
    responses={
        200: {"description": "Unread count"},
        401: {"description": "Not authenticated"},
    },
)
async def get_unread_count(
    current_user: CurrentUser,
    notification_service: NotificationSvc,
) -> UnreadCountResponse:
    """
    Get the count of unread notifications.

    This is a lightweight endpoint for polling or badge updates.
    Result is cached for 30 seconds.
    """
    count = await notification_service.get_unread_count(current_user.id)
    return UnreadCountResponse(count=count)


# =============================================================================
# Mark as Read
# =============================================================================


@router.post(
    "/{notification_id}/read",
    response_model=MessageResponse,
    summary="Mark notification as read",
    responses={
        200: {"description": "Notification marked as read"},
        401: {"description": "Not authenticated"},
        404: {"description": "Notification not found"},
    },
)
async def mark_as_read(
    notification_id: int,
    current_user: CurrentUser,
    notification_service: NotificationSvc,
) -> MessageResponse:
    """
    Mark a specific notification as read.
    """
    success = await notification_service.mark_as_read(notification_id, current_user.id)
    if success:
        return MessageResponse(message="Notification marked as read")
    return MessageResponse(message="Notification already read or not found", success=False)


@router.post(
    "/read-all",
    response_model=MessageResponse,
    summary="Mark all notifications as read",
    responses={
        200: {"description": "All notifications marked as read"},
        401: {"description": "Not authenticated"},
    },
)
async def mark_all_as_read(
    current_user: CurrentUser,
    notification_service: NotificationSvc,
) -> MessageResponse:
    """
    Mark all notifications as read for the current user.
    """
    count = await notification_service.mark_all_as_read(current_user.id)
    return MessageResponse(message=f"Marked {count} notifications as read")


# =============================================================================
# Delete Notifications
# =============================================================================


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a notification",
    responses={
        204: {"description": "Notification deleted"},
        401: {"description": "Not authenticated"},
        404: {"description": "Notification not found"},
    },
)
async def delete_notification(
    notification_id: int,
    current_user: CurrentUser,
    notification_service: NotificationSvc,
) -> None:
    """
    Delete a notification.

    Only the notification owner can delete it.
    """
    from fastapi import HTTPException
    
    deleted = await notification_service.delete_notification(notification_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or not authorized",
        )


@router.delete(
    "/",
    response_model=MessageResponse,
    summary="Delete all read notifications",
    responses={
        200: {"description": "Read notifications deleted"},
        401: {"description": "Not authenticated"},
    },
)
async def delete_all_read(
    current_user: CurrentUser,
    notification_service: NotificationSvc,
) -> MessageResponse:
    """
    Delete all read notifications for the current user.

    This helps clean up old notifications while preserving unread ones.
    """
    count = await notification_service.delete_all_read(current_user.id)
    return MessageResponse(message=f"Deleted {count} read notifications")
