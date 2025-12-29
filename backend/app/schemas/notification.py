"""Notification schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: int
    type: NotificationType
    read: bool
    data: dict[str, Any]
    actor_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Paginated notification list response."""

    items: list[NotificationResponse]
    total: int
    page: int
    per_page: int
    pages: int
    unread_count: int

    @classmethod
    def create(
        cls,
        notifications: list,
        total: int,
        page: int,
        per_page: int,
        unread_count: int = 0,
    ) -> "NotificationListResponse":
        """Create a paginated response."""
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(
            items=[NotificationResponse.model_validate(n) for n in notifications],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            unread_count=unread_count,
        )


class UnreadCountResponse(BaseModel):
    """Unread notification count response."""

    count: int

