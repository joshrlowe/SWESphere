"""WTForms form definitions for SWESphere."""
import re
from app import app, db
from app.models import User
from flask_babel import _, lazy_gettext as _l
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import BooleanField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
import sqlalchemy as sa


def validate_password_complexity(form, field):
    """Validate password meets complexity requirements."""
    password = field.data
    config = app.config

    min_length = config.get("PASSWORD_MIN_LENGTH", 8)
    if len(password) < min_length:
        raise ValidationError(
            _("Password must be at least %(min)d characters long.", min=min_length)
        )

    if config.get("PASSWORD_REQUIRE_UPPERCASE", True):
        if not re.search(r"[A-Z]", password):
            raise ValidationError(_("Password must contain at least one uppercase letter."))

    if config.get("PASSWORD_REQUIRE_LOWERCASE", True):
        if not re.search(r"[a-z]", password):
            raise ValidationError(_("Password must contain at least one lowercase letter."))

    if config.get("PASSWORD_REQUIRE_DIGIT", True):
        if not re.search(r"\d", password):
            raise ValidationError(_("Password must contain at least one digit."))

    if config.get("PASSWORD_REQUIRE_SPECIAL", False):
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise ValidationError(_("Password must contain at least one special character."))


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField(_l("Username"), validators=[DataRequired()])
    password = PasswordField(_l("Password"), validators=[DataRequired()])
    remember_me = BooleanField(_l("Remember Me"))
    submit = SubmitField(_l("Sign In"))


class RegistrationForm(FlaskForm):
    """Registration form with password complexity validation."""

    username = StringField(_l("Username"), validators=[
        DataRequired(),
        Length(min=3, max=64, message=_l("Username must be between 3 and 64 characters."))
    ])
    email = StringField(_l("Email"), validators=[DataRequired(), Email()])
    password = PasswordField(_l("Password"), validators=[
        DataRequired(),
        validate_password_complexity
    ])
    password2 = PasswordField(
        _l("Repeat Password"), validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField(_l("Register"))

    def validate_username(self, username):
        """Check username is unique and valid format."""
        # Check format (alphanumeric and underscores only)
        if not re.match(r"^[a-zA-Z0-9_]+$", username.data):
            raise ValidationError(
                _("Username can only contain letters, numbers, and underscores.")
            )

        user = db.session.scalar(sa.select(User).where(User.username == username.data))
        if user is not None:
            raise ValidationError(_("Please use a different username."))

    def validate_email(self, email):
        """Check email is unique."""
        user = db.session.scalar(sa.select(User).where(User.email == email.data))
        if user is not None:
            raise ValidationError(_("Please use a different email address."))


class EditProfileForm(FlaskForm):
    """Edit profile form."""

    username = StringField(_l("Username"), validators=[DataRequired()])
    about_me = TextAreaField(_l("About me"), validators=[Length(min=0, max=140)])
    submit = SubmitField(_l("Submit"))

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        """Check username is unique if changed."""
        if username.data != self.original_username:
            if not re.match(r"^[a-zA-Z0-9_]+$", username.data):
                raise ValidationError(
                    _("Username can only contain letters, numbers, and underscores.")
                )
            user = db.session.scalar(
                sa.select(User).where(User.username == self.username.data)
            )
            if user is not None:
                raise ValidationError(_("Please use a different username."))


class AvatarUploadForm(FlaskForm):
    """Avatar upload form."""

    avatar = FileField(_l("Upload Avatar"), validators=[
        FileAllowed(["jpg", "jpeg", "png", "gif", "webp"], _l("Images only!"))
    ])
    submit = SubmitField(_l("Upload"))


class EmptyForm(FlaskForm):
    """Empty form for CSRF-protected actions."""

    submit = SubmitField(_l("Submit"))


class PostForm(FlaskForm):
    """Post creation form."""

    post = TextAreaField(
        _l("What's happening?"), validators=[DataRequired(), Length(min=1, max=140)]
    )
    submit = SubmitField(_l("Submit"))


class CommentForm(FlaskForm):
    """Comment form for replies on posts."""

    body = TextAreaField(
        _l("Add a comment..."), validators=[DataRequired(), Length(min=1, max=280)]
    )
    submit = SubmitField(_l("Comment"))


class SearchForm(FlaskForm):
    """Search form for users and posts."""

    q = StringField(_l("Search"), validators=[DataRequired(), Length(min=1, max=100)])
    submit = SubmitField(_l("Search"))


class ResetPasswordRequestForm(FlaskForm):
    """Password reset request form."""

    email = StringField(_l("Email"), validators=[DataRequired(), Email()])
    submit = SubmitField(_l("Request Password Reset"))


class ResetPasswordForm(FlaskForm):
    """Password reset form with complexity validation."""

    password = PasswordField(_l("Password"), validators=[
        DataRequired(),
        validate_password_complexity
    ])
    password2 = PasswordField(
        _l("Repeat Password"), validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField(_l("Reset Password"))


class ChangePasswordForm(FlaskForm):
    """Change password form for authenticated users."""

    current_password = PasswordField(_l("Current Password"), validators=[DataRequired()])
    new_password = PasswordField(_l("New Password"), validators=[
        DataRequired(),
        validate_password_complexity
    ])
    new_password2 = PasswordField(
        _l("Repeat New Password"), validators=[DataRequired(), EqualTo("new_password")]
    )
    submit = SubmitField(_l("Change Password"))


class ResendVerificationForm(FlaskForm):
    """Form to request email verification resend."""

    submit = SubmitField(_l("Resend Verification Email"))
