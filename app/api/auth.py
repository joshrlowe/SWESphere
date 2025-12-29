"""API Authentication endpoints."""

from app import db, limiter
from app.api import api_bp, json_response, error_response, token_required
from app.models import User
from flask import request, g
import sqlalchemy as sa


@api_bp.route("/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
def api_login():
    """
    Authenticate and get API token.

    Request body:
        - username: string
        - password: string

    Returns:
        - token: JWT token for API authentication
        - user: User object
    """
    data = request.get_json() or {}

    if "username" not in data or "password" not in data:
        return error_response("Username and password required", 400)

    user = db.session.scalar(sa.select(User).where(User.username == data["username"]))

    if not user:
        return error_response("Invalid username or password", 401)

    # Check if account is locked
    if user.is_locked():
        return error_response("Account is temporarily locked", 403)

    if not user.check_password(data["password"]):
        user.record_failed_login()
        db.session.commit()
        return error_response("Invalid username or password", 401)

    # Successful login
    user.reset_login_attempts()
    db.session.commit()

    token = user.get_api_token()
    return json_response({"token": token, "user": user.to_dict(include_email=True)})


@api_bp.route("/auth/register", methods=["POST"])
@limiter.limit("3 per hour")
def api_register():
    """
    Register a new user.

    Request body:
        - username: string
        - email: string
        - password: string

    Returns:
        - user: Created user object
        - token: JWT token for API authentication
    """
    data = request.get_json() or {}

    required_fields = ["username", "email", "password"]
    for field in required_fields:
        if field not in data:
            return error_response(f"{field} is required", 400)

    # Check if username exists
    if db.session.scalar(sa.select(User).where(User.username == data["username"])):
        return error_response("Username already taken", 400)

    # Check if email exists
    if db.session.scalar(sa.select(User).where(User.email == data["email"])):
        return error_response("Email already registered", 400)

    user = User(username=data["username"], email=data["email"])
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    token = user.get_api_token()
    return json_response(
        {"user": user.to_dict(include_email=True), "token": token}, 201
    )


@api_bp.route("/auth/me", methods=["GET"])
@token_required
def api_me():
    """Get current authenticated user."""
    return json_response(g.current_user.to_dict(include_email=True))


@api_bp.route("/auth/refresh", methods=["POST"])
@token_required
def api_refresh_token():
    """Refresh API token."""
    new_token = g.current_user.get_api_token()
    return json_response({"token": new_token})
