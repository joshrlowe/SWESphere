"""Database models for SWESphere."""

from app import app, db, login
from datetime import datetime, timezone, timedelta
from flask_login import UserMixin
from hashlib import md5
from time import time
from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash
import json
import jwt
import sqlalchemy as sa
import sqlalchemy.orm as so


@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))


# Association tables
followers = sa.Table(
    "followers",
    db.metadata,
    sa.Column("follower_id", sa.Integer, sa.ForeignKey("user.id"), primary_key=True),
    sa.Column("followed_id", sa.Integer, sa.ForeignKey("user.id"), primary_key=True),
)

post_likes = sa.Table(
    "post_likes",
    db.metadata,
    sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), primary_key=True),
    sa.Column("post_id", sa.Integer, sa.ForeignKey("post.id"), primary_key=True),
    sa.Column("timestamp", sa.DateTime, default=lambda: datetime.now(timezone.utc)),
)


class User(db.Model, UserMixin):
    """User model with authentication and social features."""

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Email verification
    email_verified: so.Mapped[bool] = so.mapped_column(default=False)
    email_verified_at: so.Mapped[Optional[datetime]] = so.mapped_column()

    # Account lockout
    failed_login_attempts: so.Mapped[int] = so.mapped_column(default=0)
    locked_until: so.Mapped[Optional[datetime]] = so.mapped_column()
    lockout_count: so.Mapped[int] = so.mapped_column(default=0)

    # Avatar
    avatar_filename: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    # Timestamps
    created_at: so.Mapped[datetime] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    posts: so.WriteOnlyMapped["Post"] = so.relationship(back_populates="author")
    comments: so.WriteOnlyMapped["Comment"] = so.relationship(back_populates="author")
    notifications: so.WriteOnlyMapped["Notification"] = so.relationship(
        back_populates="user", foreign_keys="Notification.user_id"
    )

    following: so.WriteOnlyMapped["User"] = so.relationship(
        secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        back_populates="followers",
    )
    followers: so.WriteOnlyMapped["User"] = so.relationship(
        secondary=followers,
        primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.follower_id == id),
        back_populates="following",
    )

    liked_posts: so.WriteOnlyMapped["Post"] = so.relationship(
        secondary=post_likes,
        back_populates="liked_by",
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"

    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def avatar(self, size: int) -> str:
        """Get avatar URL - custom upload or Gravatar fallback."""
        if self.avatar_filename:
            return f"/uploads/avatars/{self.avatar_filename}"
        digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}"

    def follow(self, user: "User") -> None:
        """Follow another user."""
        if not self.is_following(user) and user.id != self.id:
            self.following.add(user)

    def unfollow(self, user: "User") -> None:
        """Unfollow a user."""
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user: "User") -> bool:
        """Check if following a user."""
        query = self.following.select().where(User.id == user.id)
        return db.session.scalar(query) is not None

    def followers_count(self) -> int:
        """Get follower count."""
        query = sa.select(sa.func.count()).select_from(
            self.followers.select().subquery()
        )
        return db.session.scalar(query)

    def following_count(self) -> int:
        """Get following count."""
        query = sa.select(sa.func.count()).select_from(
            self.following.select().subquery()
        )
        return db.session.scalar(query)

    def following_posts(self):
        """Get posts from followed users and self."""
        Author = so.aliased(User)
        Follower = so.aliased(User)
        return (
            sa.select(Post)
            .join(Post.author.of_type(Author))
            .join(Author.followers.of_type(Follower), isouter=True)
            .where(
                sa.or_(
                    Follower.id == self.id,
                    Author.id == self.id,
                )
            )
            .group_by(Post)
            .order_by(Post.timestamp.desc())
        )

    # Token methods
    def get_reset_password_token(self, expires_in: int = 600) -> str:
        """Generate password reset token."""
        return jwt.encode(
            {"reset_password": self.id, "exp": time() + expires_in},
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    @staticmethod
    def verify_reset_password_token(token: str) -> Optional["User"]:
        """Verify and return user from password reset token."""
        try:
            id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])[
                "reset_password"
            ]
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError):
            return None
        return db.session.get(User, id)

    def get_email_verification_token(self, expires_in: int = 86400) -> str:
        """Generate email verification token (24 hours default)."""
        return jwt.encode(
            {"verify_email": self.id, "exp": time() + expires_in},
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    @staticmethod
    def verify_email_token(token: str) -> Optional["User"]:
        """Verify and return user from email verification token."""
        try:
            id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])[
                "verify_email"
            ]
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError):
            return None
        return db.session.get(User, id)

    def get_api_token(self, expires_in: int = 86400) -> str:
        """Generate API authentication token."""
        return jwt.encode(
            {"user_id": self.id, "exp": time() + expires_in},
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

    @staticmethod
    def verify_api_token(token: str) -> Optional["User"]:
        """Verify API token and return user."""
        try:
            id = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])[
                "user_id"
            ]
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError):
            return None
        return db.session.get(User, id)

    # Account lockout methods
    def is_locked(self) -> bool:
        """Check if account is locked."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def record_failed_login(self) -> None:
        """Record a failed login attempt."""
        self.failed_login_attempts += 1

        max_attempts = app.config.get("MAX_LOGIN_ATTEMPTS", 5)
        if self.failed_login_attempts >= max_attempts:
            self.lock_account()

    def lock_account(self) -> None:
        """Lock the account."""
        base_duration = app.config.get("LOCKOUT_DURATION_MINUTES", 15)
        progressive = app.config.get("LOCKOUT_PROGRESSIVE", True)

        if progressive:
            duration = base_duration * (2**self.lockout_count)
        else:
            duration = base_duration

        self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration)
        self.lockout_count += 1
        self.failed_login_attempts = 0

    def reset_login_attempts(self) -> None:
        """Reset failed login counter on successful login."""
        self.failed_login_attempts = 0

    # Like methods
    def like_post(self, post: "Post") -> None:
        """Like a post."""
        if not self.has_liked(post):
            self.liked_posts.add(post)

    def unlike_post(self, post: "Post") -> None:
        """Unlike a post."""
        if self.has_liked(post):
            self.liked_posts.remove(post)

    def has_liked(self, post: "Post") -> bool:
        """Check if user has liked a post."""
        query = self.liked_posts.select().where(Post.id == post.id)
        return db.session.scalar(query) is not None

    # Notification methods
    def unread_notification_count(self) -> int:
        """Get count of unread notifications."""
        return (
            db.session.scalar(
                sa.select(sa.func.count())
                .select_from(Notification)
                .where(Notification.user_id == self.id, Notification.read == False)
            )
            or 0
        )

    def add_notification(
        self, name: str, data: dict, actor_id: int = None
    ) -> "Notification":
        """Add a notification for this user."""
        notification = Notification(
            name=name,
            payload_json=json.dumps(data),
            user_id=self.id,
            actor_id=actor_id,
        )
        db.session.add(notification)
        return notification

    def to_dict(self, include_email: bool = False) -> dict:
        """Convert user to dictionary for API responses."""
        data = {
            "id": self.id,
            "username": self.username,
            "about_me": self.about_me,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "avatar": self.avatar(128),
            "followers_count": self.followers_count(),
            "following_count": self.following_count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_email:
            data["email"] = self.email
            data["email_verified"] = self.email_verified
        return data


class Post(db.Model):
    """Post model."""

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc)
    )
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    author: so.Mapped[User] = so.relationship(back_populates="posts")

    # Relationships
    comments: so.WriteOnlyMapped["Comment"] = so.relationship(
        back_populates="post", cascade="all, delete-orphan"
    )
    liked_by: so.WriteOnlyMapped["User"] = so.relationship(
        secondary=post_likes,
        back_populates="liked_posts",
    )

    def __repr__(self) -> str:
        return f"<Post {self.body}>"

    def likes_count(self) -> int:
        """Get number of likes on this post."""
        query = sa.select(sa.func.count()).select_from(
            self.liked_by.select().subquery()
        )
        return db.session.scalar(query) or 0

    def comments_count(self) -> int:
        """Get number of comments on this post."""
        query = sa.select(sa.func.count()).select_from(
            self.comments.select().subquery()
        )
        return db.session.scalar(query) or 0

    def to_dict(self) -> dict:
        """Convert post to dictionary for API responses."""
        return {
            "id": self.id,
            "body": self.body,
            "timestamp": self.timestamp.isoformat(),
            "author": self.author.to_dict(),
            "likes_count": self.likes_count(),
            "comments_count": self.comments_count(),
        }


class Comment(db.Model):
    """Comment model for post replies."""

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(280))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc)
    )
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    post_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Post.id), index=True)

    # Relationships
    author: so.Mapped[User] = so.relationship(back_populates="comments")
    post: so.Mapped[Post] = so.relationship(back_populates="comments")

    def __repr__(self) -> str:
        return f"<Comment {self.body[:20]}>"

    def to_dict(self) -> dict:
        """Convert comment to dictionary for API responses."""
        return {
            "id": self.id,
            "body": self.body,
            "timestamp": self.timestamp.isoformat(),
            "author": self.author.to_dict(),
            "post_id": self.post_id,
        }


class Notification(db.Model):
    """Notification model for user notifications."""

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(128), index=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    actor_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey(User.id))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc)
    )
    payload_json: so.Mapped[str] = so.mapped_column(sa.Text)
    read: so.Mapped[bool] = so.mapped_column(default=False)

    # Relationships
    user: so.Mapped[User] = so.relationship(
        back_populates="notifications", foreign_keys=[user_id]
    )
    actor: so.Mapped[Optional[User]] = so.relationship(foreign_keys=[actor_id])

    def __repr__(self) -> str:
        return f"<Notification {self.name}>"

    def get_data(self) -> dict:
        """Get notification payload as dictionary."""
        return json.loads(self.payload_json)

    def to_dict(self) -> dict:
        """Convert notification to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "data": self.get_data(),
            "read": self.read,
            "actor": self.actor.to_dict() if self.actor else None,
        }
