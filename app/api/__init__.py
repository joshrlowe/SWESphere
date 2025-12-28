"""REST API Blueprint for SWESphere."""
from flask import Blueprint, jsonify, request, g
from functools import wraps

api_bp = Blueprint("api", __name__)


def token_required(f):
    """Decorator to require API token authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from app.models import User

        token = None
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"error": "Token is missing"}), 401

        user = User.verify_api_token(token)
        if not user:
            return jsonify({"error": "Token is invalid or expired"}), 401

        g.current_user = user
        return f(*args, **kwargs)

    return decorated


def json_response(data, status=200):
    """Create a JSON response with proper headers."""
    response = jsonify(data)
    response.status_code = status
    return response


def error_response(message, status=400):
    """Create an error JSON response."""
    return json_response({"error": message}, status)


# Import routes after blueprint is created
from app.api import auth, users, posts, notifications
