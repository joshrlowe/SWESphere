"""User model with authentication and social features."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.models.mixins import BaseModelMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.notification import Notification
    from app.models.post import Post


class User(Base, BaseModelMixin, SoftDeleteMixin):
    """
    User model for authentication and user profiles.
    
    Attributes:
        id: Primary key
        username: Unique username (3-64 chars, alphanumeric + underscore)
        email: Unique email address
        password_hash: Bcrypt hashed password
        display_name: Optional display name
        bio: User biography/about me
        avatar_url: Custom avatar URL (if not using Gravatar)
        location: User location
        website: User website URL
        
        is_active: Whether account is active
        is_verified: Whether user is verified (blue check)
        is_superuser: Whether user has admin privileges
        email_verified: Whether email has been verified
        
        failed_login_attempts: Count of failed login attempts
        locked_until: Account lockout expiry time
        last_login: Last successful login timestamp
    
    Relationships:
        posts: User's posts
        comments: User's comments
        notifications: User's notifications
        followers: Users following this user
        following: Users this user follows
        liked_posts: Posts this user has liked
    """

    __tablename__ = "users"

    # ===================
    # Primary Key
    # ===================
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ===================
    # Authentication
    # ===================
    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # ===================
    # Profile
    # ===================
    display_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Custom avatar URL. If None, Gravatar is used.",
    )
    location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # ===================
    # Status Flags
    # ===================
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Verified account (blue checkmark)",
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # ===================
    # Security
    # ===================
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="Account locked until this timestamp",
    )
    last_login: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    # ===================
    # Denormalized Counts
    # ===================
    followers_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    following_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    posts_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # ===================
    # Relationships
    # ===================
    posts: Mapped[list["Post"]] = relationship(
        "Post",
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Post.created_at.desc()",
    )

    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        foreign_keys="Notification.user_id",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Notification.created_at.desc()",
    )

    # Self-referential many-to-many for followers/following
    followers: Mapped[list["User"]] = relationship(
        "User",
        secondary="followers",
        primaryjoin="User.id == followers.c.followed_id",
        secondaryjoin="User.id == followers.c.follower_id",
        back_populates="following",
        lazy="selectin",
    )

    following: Mapped[list["User"]] = relationship(
        "User",
        secondary="followers",
        primaryjoin="User.id == followers.c.follower_id",
        secondaryjoin="User.id == followers.c.followed_id",
        back_populates="followers",
        lazy="selectin",
    )

    # Posts liked by this user
    liked_posts: Mapped[list["Post"]] = relationship(
        "Post",
        secondary="post_likes",
        back_populates="liked_by",
        lazy="selectin",
    )

    # ===================
    # Indexes
    # ===================
    __table_args__ = (
        Index("ix_users_username_lower", "username"),
        Index("ix_users_email_lower", "email"),
        Index("ix_users_created_at", "created_at"),
    )

    # ===================
    # Password Methods
    # ===================
    def set_password(self, password: str) -> None:
        """
        Hash and set the user's password.
        
        Args:
            password: Plain text password to hash
        """
        self.password_hash = hash_password(password)

    def check_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        return verify_password(password, self.password_hash)

    # ===================
    # Avatar Methods
    # ===================
    @property
    def avatar(self) -> str:
        """
        Get the user's avatar URL.
        
        Returns custom avatar if set, otherwise Gravatar.
        
        Returns:
            Avatar URL
        """
        if self.avatar_url:
            return self.avatar_url
        return self.gravatar_url()

    def gravatar_url(self, size: int = 128) -> str:
        """
        Generate Gravatar URL from email.
        
        Args:
            size: Avatar size in pixels
            
        Returns:
            Gravatar URL
        """
        email_hash = hashlib.md5(
            self.email.lower().encode("utf-8")
        ).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s={size}"

    # ===================
    # Account Lockout
    # ===================
    def is_locked(self) -> bool:
        """
        Check if the account is currently locked.
        
        Returns:
            True if account is locked
        """
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def record_failed_login(self) -> None:
        """
        Record a failed login attempt.
        
        Locks account after 5 failed attempts for 15 minutes.
        Progressive lockout: duration doubles with each lockout.
        """
        self.failed_login_attempts += 1
        
        if self.failed_login_attempts >= 5:
            # Calculate lockout duration (15 min * 2^(lockouts-1))
            lockout_count = (self.failed_login_attempts - 5) // 5 + 1
            lockout_minutes = 15 * (2 ** min(lockout_count - 1, 4))  # Max 4 hours
            self.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=lockout_minutes
            )

    def reset_login_attempts(self) -> None:
        """Reset login attempts after successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.now(timezone.utc)

    # ===================
    # Follow Methods
    # ===================
    def is_following(self, user: "User") -> bool:
        """
        Check if this user is following another user.
        
        Args:
            user: User to check
            
        Returns:
            True if following
        """
        return user in self.following

    def follow(self, user: "User") -> bool:
        """
        Follow another user.
        
        Args:
            user: User to follow
            
        Returns:
            True if successfully followed (wasn't already following)
        """
        if user.id == self.id:
            return False
        if not self.is_following(user):
            self.following.append(user)
            self.following_count += 1
            user.followers_count += 1
            return True
        return False

    def unfollow(self, user: "User") -> bool:
        """
        Unfollow a user.
        
        Args:
            user: User to unfollow
            
        Returns:
            True if successfully unfollowed (was following)
        """
        if self.is_following(user):
            self.following.remove(user)
            self.following_count = max(0, self.following_count - 1)
            user.followers_count = max(0, user.followers_count - 1)
            return True
        return False

    # ===================
    # Serialization
    # ===================
    def to_dict(
        self,
        include_email: bool = False,
        include_private: bool = False,
    ) -> dict[str, Any]:
        """
        Convert user to dictionary for API responses.
        
        Args:
            include_email: Include email in response
            include_private: Include private fields
            
        Returns:
            Dictionary representation
        """
        data = {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "bio": self.bio,
            "avatar_url": self.avatar,
            "location": self.location,
            "website": self.website,
            "is_verified": self.is_verified,
            "followers_count": self.followers_count,
            "following_count": self.following_count,
            "posts_count": self.posts_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        if include_email:
            data["email"] = self.email
            data["email_verified"] = self.email_verified

        if include_private:
            data["is_active"] = self.is_active
            data["is_superuser"] = self.is_superuser
            data["last_login"] = (
                self.last_login.isoformat() if self.last_login else None
            )

        return data

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r})>"
