"""Pytest configuration and fixtures."""
import os
import pytest

# Set test environment before importing app
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["WTF_CSRF_ENABLED"] = "False"

from app import app as flask_app, db
from app.models import User, Post


@pytest.fixture
def app():
    """Create application for testing."""
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "RATELIMIT_ENABLED": False,
    })

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        # Get fresh reference
        user = db.session.get(User, user.id)
        return user


@pytest.fixture
def sample_users(app):
    """Create multiple sample users for testing."""
    with app.app_context():
        users = []
        for i in range(3):
            user = User(username=f"user{i}", email=f"user{i}@example.com")
            user.set_password("password123")
            db.session.add(user)
            users.append(user)
        db.session.commit()
        return [db.session.get(User, u.id) for u in users]


@pytest.fixture
def auth_client(client, sample_user, app):
    """Create an authenticated test client."""
    with app.app_context():
        # Re-fetch user in this context
        user = db.session.query(User).filter_by(username="testuser").first()
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
            sess["_fresh"] = True
    return client
