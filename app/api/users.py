"""API User endpoints."""
from app import db
from app.api import api_bp, json_response, error_response, token_required
from app.models import User, Post
from flask import request, g
import sqlalchemy as sa


@api_bp.route("/users", methods=["GET"])
@token_required
def api_get_users():
    """
    Get list of users with pagination.

    Query params:
        - page: int (default 1)
        - per_page: int (default 20, max 100)
        - q: string (optional search query)
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    search = request.args.get("q", "", type=str)

    query = sa.select(User)

    if search:
        query = query.where(
            sa.or_(
                User.username.ilike(f"%{search}%"),
                User.about_me.ilike(f"%{search}%")
            )
        )

    query = query.order_by(User.username)
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return json_response({
        "users": [user.to_dict() for user in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    })


@api_bp.route("/users/<username>", methods=["GET"])
@token_required
def api_get_user(username):
    """Get a specific user by username."""
    user = db.session.scalar(sa.select(User).where(User.username == username))
    if not user:
        return error_response("User not found", 404)

    data = user.to_dict()
    data["is_following"] = g.current_user.is_following(user)
    data["is_self"] = g.current_user.id == user.id

    return json_response(data)


@api_bp.route("/users/<username>/posts", methods=["GET"])
@token_required
def api_get_user_posts(username):
    """Get posts by a specific user."""
    user = db.session.scalar(sa.select(User).where(User.username == username))
    if not user:
        return error_response("User not found", 404)

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = user.posts.select().order_by(Post.timestamp.desc())
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    posts_data = []
    for post in pagination.items:
        post_dict = post.to_dict()
        post_dict["liked"] = g.current_user.has_liked(post)
        posts_data.append(post_dict)

    return json_response({
        "posts": posts_data,
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    })


@api_bp.route("/users/<username>/follow", methods=["POST"])
@token_required
def api_follow_user(username):
    """Follow a user."""
    user = db.session.scalar(sa.select(User).where(User.username == username))
    if not user:
        return error_response("User not found", 404)

    if user.id == g.current_user.id:
        return error_response("Cannot follow yourself", 400)

    if g.current_user.is_following(user):
        return error_response("Already following this user", 400)

    g.current_user.follow(user)

    # Create notification
    user.add_notification(
        "new_follower",
        {"username": g.current_user.username},
        actor_id=g.current_user.id
    )

    db.session.commit()

    return json_response({"message": f"Now following {username}"})


@api_bp.route("/users/<username>/unfollow", methods=["POST"])
@token_required
def api_unfollow_user(username):
    """Unfollow a user."""
    user = db.session.scalar(sa.select(User).where(User.username == username))
    if not user:
        return error_response("User not found", 404)

    if not g.current_user.is_following(user):
        return error_response("Not following this user", 400)

    g.current_user.unfollow(user)
    db.session.commit()

    return json_response({"message": f"Unfollowed {username}"})


@api_bp.route("/users/<username>/followers", methods=["GET"])
@token_required
def api_get_followers(username):
    """Get followers of a user."""
    user = db.session.scalar(sa.select(User).where(User.username == username))
    if not user:
        return error_response("User not found", 404)

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = user.followers.select()
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return json_response({
        "users": [u.to_dict() for u in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    })


@api_bp.route("/users/<username>/following", methods=["GET"])
@token_required
def api_get_following(username):
    """Get users that a user is following."""
    user = db.session.scalar(sa.select(User).where(User.username == username))
    if not user:
        return error_response("User not found", 404)

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = user.following.select()
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return json_response({
        "users": [u.to_dict() for u in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    })
