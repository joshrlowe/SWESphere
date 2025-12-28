"""Tests for form validation."""
import pytest
from app.forms import (
    LoginForm,
    RegistrationForm,
    EditProfileForm,
    PostForm,
    ResetPasswordForm,
    ResetPasswordRequestForm,
)


class TestLoginForm:
    """Tests for LoginForm."""

    def test_valid_login_form(self, app):
        """Test valid login form."""
        with app.app_context():
            form = LoginForm(data={
                "username": "testuser",
                "password": "password123",
            })
            assert form.validate() is True

    def test_empty_username(self, app):
        """Test login form with empty username."""
        with app.app_context():
            form = LoginForm(data={
                "username": "",
                "password": "password123",
            })
            assert form.validate() is False
            assert "username" in form.errors

    def test_empty_password(self, app):
        """Test login form with empty password."""
        with app.app_context():
            form = LoginForm(data={
                "username": "testuser",
                "password": "",
            })
            assert form.validate() is False
            assert "password" in form.errors


class TestRegistrationForm:
    """Tests for RegistrationForm."""

    def test_valid_registration(self, app):
        """Test valid registration form."""
        with app.app_context():
            form = RegistrationForm(data={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123",
                "password2": "password123",
            })
            assert form.validate() is True

    def test_password_mismatch(self, app):
        """Test registration with mismatched passwords."""
        with app.app_context():
            form = RegistrationForm(data={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123",
                "password2": "different123",
            })
            assert form.validate() is False
            assert "password2" in form.errors

    def test_invalid_email(self, app):
        """Test registration with invalid email."""
        with app.app_context():
            form = RegistrationForm(data={
                "username": "newuser",
                "email": "invalid-email",
                "password": "password123",
                "password2": "password123",
            })
            assert form.validate() is False
            assert "email" in form.errors


class TestPostForm:
    """Tests for PostForm."""

    def test_valid_post(self, app):
        """Test valid post form."""
        with app.app_context():
            form = PostForm(data={
                "post": "This is a valid post!",
            })
            assert form.validate() is True

    def test_empty_post(self, app):
        """Test empty post."""
        with app.app_context():
            form = PostForm(data={
                "post": "",
            })
            assert form.validate() is False

    def test_post_too_long(self, app):
        """Test post exceeding character limit."""
        with app.app_context():
            form = PostForm(data={
                "post": "x" * 141,  # Exceeds 140 char limit
            })
            assert form.validate() is False


class TestEditProfileForm:
    """Tests for EditProfileForm."""

    def test_valid_edit_profile(self, app):
        """Test valid profile edit."""
        with app.app_context():
            form = EditProfileForm("originaluser", data={
                "username": "newusername",
                "about_me": "New bio",
            })
            assert form.validate() is True

    def test_about_me_too_long(self, app):
        """Test about_me exceeding character limit."""
        with app.app_context():
            form = EditProfileForm("testuser", data={
                "username": "testuser",
                "about_me": "x" * 141,  # Exceeds 140 char limit
            })
            assert form.validate() is False
