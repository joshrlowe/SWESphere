"""Tests for database models."""
from datetime import datetime, timezone, timedelta
import pytest
from app import db
from app.models import User, Post


class TestUserModel:
    """Tests for the User model."""

    def test_password_hashing(self, app):
        """Test password hashing and verification."""
        with app.app_context():
            user = User(username="testuser", email="test@example.com")
            user.set_password("correctpassword")

            assert user.check_password("correctpassword") is True
            assert user.check_password("wrongpassword") is False

    def test_avatar_url(self, app):
        """Test Gravatar avatar URL generation."""
        with app.app_context():
            user = User(username="john", email="john@example.com")
            avatar_url = user.avatar(128)

            assert "gravatar.com/avatar" in avatar_url
            assert "s=128" in avatar_url
            assert "d=identicon" in avatar_url

    def test_user_repr(self, app):
        """Test User string representation."""
        with app.app_context():
            user = User(username="testuser", email="test@example.com")
            assert repr(user) == "<User testuser>"

    def test_follow_user(self, sample_users, app):
        """Test following a user."""
        with app.app_context():
            user1 = db.session.query(User).filter_by(username="user0").first()
            user2 = db.session.query(User).filter_by(username="user1").first()

            assert user1.is_following(user2) is False

            user1.follow(user2)
            db.session.commit()

            assert user1.is_following(user2) is True
            assert user1.following_count() == 1
            assert user2.followers_count() == 1

    def test_unfollow_user(self, sample_users, app):
        """Test unfollowing a user."""
        with app.app_context():
            user1 = db.session.query(User).filter_by(username="user0").first()
            user2 = db.session.query(User).filter_by(username="user1").first()

            user1.follow(user2)
            db.session.commit()

            user1.unfollow(user2)
            db.session.commit()

            assert user1.is_following(user2) is False
            assert user1.following_count() == 0

    def test_cannot_follow_self(self, sample_user, app):
        """Test that a user cannot follow themselves."""
        with app.app_context():
            user = db.session.query(User).filter_by(username="testuser").first()
            user.follow(user)
            db.session.commit()

            # The follow method should prevent this
            assert user.following_count() == 0

    def test_password_reset_token(self, sample_user, app):
        """Test password reset token generation and verification."""
        with app.app_context():
            user = db.session.query(User).filter_by(username="testuser").first()
            token = user.get_reset_password_token(expires_in=600)

            assert token is not None
            verified_user = User.verify_reset_password_token(token)
            assert verified_user.id == user.id

    def test_invalid_reset_token(self, app):
        """Test invalid password reset token."""
        with app.app_context():
            result = User.verify_reset_password_token("invalid-token")
            assert result is None


class TestPostModel:
    """Tests for the Post model."""

    def test_create_post(self, sample_user, app):
        """Test creating a post."""
        with app.app_context():
            user = db.session.query(User).filter_by(username="testuser").first()
            post = Post(body="Test post content", author=user)
            db.session.add(post)
            db.session.commit()

            assert post.id is not None
            assert post.body == "Test post content"
            assert post.author.username == "testuser"

    def test_post_timestamp(self, sample_user, app):
        """Test that posts have timestamps."""
        with app.app_context():
            user = db.session.query(User).filter_by(username="testuser").first()
            post = Post(body="Test post", author=user)
            db.session.add(post)
            db.session.commit()

            assert post.timestamp is not None
            assert isinstance(post.timestamp, datetime)

    def test_post_repr(self, sample_user, app):
        """Test Post string representation."""
        with app.app_context():
            user = db.session.query(User).filter_by(username="testuser").first()
            post = Post(body="Hello World", author=user)
            assert repr(post) == "<Post Hello World>"

    def test_following_posts(self, sample_users, app):
        """Test getting posts from followed users."""
        with app.app_context():
            users = [db.session.query(User).filter_by(username=f"user{i}").first() for i in range(3)]

            # Create posts
            now = datetime.now(timezone.utc)
            posts = []
            for i, user in enumerate(users):
                post = Post(
                    body=f"Post from {user.username}",
                    author=user,
                    timestamp=now + timedelta(seconds=i)
                )
                db.session.add(post)
                posts.append(post)
            db.session.commit()

            # User0 follows User1
            users[0].follow(users[1])
            db.session.commit()

            # User0 should see their own posts and User1's posts
            following_posts = db.session.scalars(users[0].following_posts()).all()
            assert len(following_posts) == 2

            # Most recent first
            assert following_posts[0].author.username == "user1"
            assert following_posts[1].author.username == "user0"
