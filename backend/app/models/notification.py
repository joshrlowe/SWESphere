"""Notification model with typed notification types."""

from __future__ import annotations

import enum
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import BaseModelMixin

if TYPE_CHECKING:
    from app.models.user import User


class NotificationType(str, enum.Enum):
    """
    Enumeration of notification types.

    Each type has associated data expectations:
    - NEW_FOLLOWER: {follower_id, follower_username}
    - POST_LIKED: {post_id, liker_id, liker_username}
    - POST_COMMENTED: {post_id, comment_id, commenter_id, commenter_username}
    - POST_REPOSTED: {post_id, reposter_id, reposter_username}
    - MENTIONED: {post_id, mentioner_id, mentioner_username}
    - REPLY: {post_id, reply_id, replier_id, replier_username}
    - FOLLOW_REQUEST: {requester_id, requester_username}
    - SYSTEM: {message}
    """

    NEW_FOLLOWER = "new_follower"
    POST_LIKED = "post_liked"
    POST_COMMENTED = "post_commented"
    POST_REPOSTED = "post_reposted"
    MENTIONED = "mentioned"
    REPLY = "reply"
    FOLLOW_REQUEST = "follow_request"
    SYSTEM = "system"


class Notification(Base, BaseModelMixin):
    """
    Notification model for user notifications.

    Notifications are created when certain events occur (new follower,
    post liked, etc.) and are delivered to users via the API and
    optionally push notifications.

    Attributes:
        id: Primary key
        type: Type of notification (enum)
        payload_json: JSON-encoded additional data
        read: Whether the notification has been read
        user_id: Foreign key to notification recipient
        actor_id: Foreign key to user who triggered the notification

    Relationships:
        user: User receiving the notification
        actor: User who triggered the notification
    """

    __tablename__ = "notifications"

    # ===================
    # Primary Key
    # ===================
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ===================
    # Notification Details
    # ===================
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False, length=50),
        nullable=False,
        index=True,
        doc="Type of notification",
    )

    payload_json: Mapped[str] = mapped_column(
        Text,
        default="{}",
        nullable=False,
        doc="JSON-encoded notification data",
    )

    read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether notification has been read",
    )

    # ===================
    # Foreign Keys
    # ===================
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User receiving the notification",
    )

    actor_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User who triggered the notification",
    )

    # ===================
    # Relationships
    # ===================
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
        foreign_keys=[user_id],
        lazy="selectin",
    )

    actor: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[actor_id],
        lazy="selectin",
    )

    # ===================
    # Indexes
    # ===================
    __table_args__ = (
        # For fetching user's notifications
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
        # For fetching unread notifications
        Index("ix_notifications_user_id_read", "user_id", "read"),
        # For filtering by type
        Index("ix_notifications_user_id_type", "user_id", "type"),
    )

    # ===================
    # Payload Methods
    # ===================
    @property
    def data(self) -> dict[str, Any]:
        """
        Get the notification payload as a dictionary.

        Returns:
            Parsed JSON payload
        """
        try:
            return json.loads(self.payload_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    @data.setter
    def data(self, value: dict[str, Any]) -> None:
        """
        Set the notification payload.

        Args:
            value: Dictionary to serialize as JSON
        """
        self.payload_json = json.dumps(value)

    def get_data(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the notification payload.

        Args:
            key: Key to look up
            default: Default value if key not found

        Returns:
            Value from payload or default
        """
        return self.data.get(key, default)

    def set_data(self, key: str, value: Any) -> None:
        """
        Set a value in the notification payload.

        Args:
            key: Key to set
            value: Value to store
        """
        data = self.data
        data[key] = value
        self.data = data

    # ===================
    # Read Status Methods
    # ===================
    def mark_as_read(self) -> None:
        """Mark the notification as read."""
        self.read = True

    def mark_as_unread(self) -> None:
        """Mark the notification as unread."""
        self.read = False

    # ===================
    # Factory Methods
    # ===================
    @classmethod
    def create_new_follower(
        cls,
        user_id: int,
        follower_id: int,
        follower_username: str,
    ) -> "Notification":
        """
        Create a new follower notification.

        Args:
            user_id: User being followed
            follower_id: User who followed
            follower_username: Follower's username

        Returns:
            New Notification instance
        """
        notification = cls(
            type=NotificationType.NEW_FOLLOWER,
            user_id=user_id,
            actor_id=follower_id,
        )
        notification.data = {
            "follower_id": follower_id,
            "follower_username": follower_username,
        }
        return notification

    @classmethod
    def create_post_liked(
        cls,
        user_id: int,
        post_id: int,
        liker_id: int,
        liker_username: str,
    ) -> "Notification":
        """
        Create a post liked notification.

        Args:
            user_id: Post author
            post_id: Post that was liked
            liker_id: User who liked
            liker_username: Liker's username

        Returns:
            New Notification instance
        """
        notification = cls(
            type=NotificationType.POST_LIKED,
            user_id=user_id,
            actor_id=liker_id,
        )
        notification.data = {
            "post_id": post_id,
            "liker_id": liker_id,
            "liker_username": liker_username,
        }
        return notification

    @classmethod
    def create_post_commented(
        cls,
        user_id: int,
        post_id: int,
        comment_id: int,
        commenter_id: int,
        commenter_username: str,
    ) -> "Notification":
        """
        Create a post commented notification.

        Args:
            user_id: Post author
            post_id: Post that was commented on
            comment_id: The new comment
            commenter_id: User who commented
            commenter_username: Commenter's username

        Returns:
            New Notification instance
        """
        notification = cls(
            type=NotificationType.POST_COMMENTED,
            user_id=user_id,
            actor_id=commenter_id,
        )
        notification.data = {
            "post_id": post_id,
            "comment_id": comment_id,
            "commenter_id": commenter_id,
            "commenter_username": commenter_username,
        }
        return notification

    @classmethod
    def create_mentioned(
        cls,
        user_id: int,
        post_id: int,
        mentioner_id: int,
        mentioner_username: str,
    ) -> "Notification":
        """
        Create a mention notification.

        Args:
            user_id: User who was mentioned
            post_id: Post containing the mention
            mentioner_id: User who mentioned
            mentioner_username: Mentioner's username

        Returns:
            New Notification instance
        """
        notification = cls(
            type=NotificationType.MENTIONED,
            user_id=user_id,
            actor_id=mentioner_id,
        )
        notification.data = {
            "post_id": post_id,
            "mentioner_id": mentioner_id,
            "mentioner_username": mentioner_username,
        }
        return notification

    @classmethod
    def create_system(
        cls,
        user_id: int,
        message: str,
    ) -> "Notification":
        """
        Create a system notification.

        Args:
            user_id: User to notify
            message: System message

        Returns:
            New Notification instance
        """
        notification = cls(
            type=NotificationType.SYSTEM,
            user_id=user_id,
            actor_id=None,
        )
        notification.data = {"message": message}
        return notification

    # ===================
    # Message Generation
    # ===================
    @property
    def message(self) -> str:
        """
        Generate a human-readable message for this notification.

        Returns:
            Notification message string
        """
        data = self.data
        actor_name = data.get(
            "follower_username",
            data.get(
                "liker_username",
                data.get(
                    "commenter_username", data.get("mentioner_username", "Someone")
                ),
            ),
        )

        messages = {
            NotificationType.NEW_FOLLOWER: f"{actor_name} started following you",
            NotificationType.POST_LIKED: f"{actor_name} liked your post",
            NotificationType.POST_COMMENTED: f"{actor_name} commented on your post",
            NotificationType.POST_REPOSTED: f"{actor_name} reposted your post",
            NotificationType.MENTIONED: f"{actor_name} mentioned you in a post",
            NotificationType.REPLY: f"{actor_name} replied to your post",
            NotificationType.FOLLOW_REQUEST: f"{actor_name} requested to follow you",
            NotificationType.SYSTEM: data.get("message", "System notification"),
        }

        return messages.get(self.type, "You have a notification")

    def to_dict(self, include_actor: bool = True) -> dict[str, Any]:
        """
        Convert notification to dictionary for API responses.

        Args:
            include_actor: Include actor user details

        Returns:
            Dictionary representation
        """
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type.value,
            "message": self.message,
            "data": self.data,
            "read": self.read,
            "user_id": self.user_id,
            "actor_id": self.actor_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        if include_actor and self.actor:
            result["actor"] = {
                "id": self.actor.id,
                "username": self.actor.username,
                "display_name": self.actor.display_name,
                "avatar_url": self.actor.avatar,
                "is_verified": self.actor.is_verified,
            }

        return result

    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, type={self.type.value}, "
            f"user_id={self.user_id}, read={self.read})>"
        )
