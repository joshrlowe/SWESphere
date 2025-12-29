"""Tests for web routes."""

import pytest
from app import db
from app.models import User


class TestPublicRoutes:
    """Tests for public (unauthenticated) routes."""

    def test_login_page(self, client):
        """Test login page loads."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"Sign In" in response.data

    def test_register_page(self, client):
        """Test registration page loads."""
        response = client.get("/register")
        assert response.status_code == 200
        assert b"Register" in response.data

    def test_favicon(self, client):
        """Test favicon endpoint."""
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        assert response.content_type == "image/png"

    def test_index_redirects_to_login(self, client):
        """Test index redirects unauthenticated users to login."""
        response = client.get("/")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_reset_password_request_page(self, client):
        """Test password reset request page loads."""
        response = client.get("/reset_password_request")
        assert response.status_code == 200
        assert b"Reset Password" in response.data


class TestAuthentication:
    """Tests for authentication flows."""

    def test_register_user(self, client, app):
        """Test user registration."""
        response = client.post(
            "/register",
            data={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "StrongPass123!",
                "password2": "StrongPass123!",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        with app.app_context():
            user = db.session.query(User).filter_by(username="newuser").first()
            assert user is not None
            assert user.email == "newuser@example.com"

    def test_register_duplicate_username(self, client, sample_user, app):
        """Test registration with duplicate username fails."""
        with app.app_context():
            response = client.post(
                "/register",
                data={
                    "username": "testuser",  # Already exists
                    "email": "another@example.com",
                    "password": "password123",
                    "password2": "password123",
                },
            )

            assert response.status_code == 200
            assert b"Please use a different username" in response.data

    def test_login_valid_credentials(self, client, sample_user, app):
        """Test login with valid credentials."""
        response = client.post(
            "/login",
            data={
                "username": "testuser",
                "password": "password123",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

    def test_login_invalid_credentials(self, client, sample_user, app):
        """Test login with invalid credentials."""
        response = client.post(
            "/login",
            data={
                "username": "testuser",
                "password": "wrongpassword",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Invalid username or password" in response.data

    def test_logout(self, auth_client, app):
        """Test logout functionality."""
        response = auth_client.get("/logout", follow_redirects=True)
        assert response.status_code == 200


class TestAuthenticatedRoutes:
    """Tests for authenticated routes."""

    def test_index_page(self, auth_client, app):
        """Test index page for authenticated users."""
        response = auth_client.get("/")
        assert response.status_code == 200

    def test_explore_page(self, auth_client, app):
        """Test explore page."""
        response = auth_client.get("/explore")
        assert response.status_code == 200

    def test_user_profile(self, auth_client, sample_user, app):
        """Test user profile page."""
        response = auth_client.get("/user/testuser")
        assert response.status_code == 200
        assert b"testuser" in response.data

    def test_edit_profile_page(self, auth_client, app):
        """Test edit profile page loads."""
        response = auth_client.get("/edit_profile")
        assert response.status_code == 200

    def test_edit_profile_submit(self, auth_client, app):
        """Test editing profile."""
        response = auth_client.post(
            "/edit_profile",
            data={
                "username": "testuser",
                "about_me": "Updated bio",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

    def test_create_post(self, auth_client, app):
        """Test creating a new post."""
        response = auth_client.post(
            "/",
            data={
                "post": "This is a test post!",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200


class TestSecurityHeaders:
    """Tests for security headers."""

    def test_csp_header(self, auth_client, app):
        """Test Content-Security-Policy header is present."""
        response = auth_client.get("/")
        assert "Content-Security-Policy" in response.headers

    def test_xframe_options(self, auth_client, app):
        """Test X-Frame-Options header."""
        response = auth_client.get("/")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_xcontent_type_options(self, auth_client, app):
        """Test X-Content-Type-Options header."""
        response = auth_client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_hsts_header(self, auth_client, app):
        """Test Strict-Transport-Security header."""
        response = auth_client.get("/")
        assert "Strict-Transport-Security" in response.headers
