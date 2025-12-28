"""API Post endpoints."""
from app import db
from app.api import api_bp, json_response, error_response, token_required
from app.models import User, Post, Comment
from flask import request, g
import sqlalchemy as sa


@api_bp.route("/posts", methods=["GET"])
@token_required
def api_get_posts():
    """
    Get posts feed.

    Query params:
        - page: int (default 1)
        - per_page: int (default 20, max 100)
        - feed: string ("home" for following feed, "explore" for all)
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    feed_type = request.args.get("feed", "home", type=str)

    if feed_type == "home":
        query = g.current_user.following_posts()
    else:
        query = sa.select(Post).order_by(Post.timestamp.desc())

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


@api_bp.route("/posts", methods=["POST"])
@token_required
def api_create_post():
    """
    Create a new post.

    Request body:
        - body: string (1-140 characters)
    """
    data = request.get_json() or {}

    if "body" not in data:
        return error_response("Post body is required", 400)

    body = data["body"].strip()
    if len(body) < 1 or len(body) > 140:
        return error_response("Post must be between 1 and 140 characters", 400)

    post = Post(body=body, author=g.current_user)
    db.session.add(post)
    db.session.commit()

    return json_response(post.to_dict(), 201)


@api_bp.route("/posts/<int:post_id>", methods=["GET"])
@token_required
def api_get_post(post_id):
    """Get a specific post."""
    post = db.session.get(Post, post_id)
    if not post:
        return error_response("Post not found", 404)

    post_dict = post.to_dict()
    post_dict["liked"] = g.current_user.has_liked(post)

    return json_response(post_dict)


@api_bp.route("/posts/<int:post_id>", methods=["DELETE"])
@token_required
def api_delete_post(post_id):
    """Delete a post (only by author)."""
    post = db.session.get(Post, post_id)
    if not post:
        return error_response("Post not found", 404)

    if post.author.id != g.current_user.id:
        return error_response("Not authorized to delete this post", 403)

    db.session.delete(post)
    db.session.commit()

    return json_response({"message": "Post deleted"})


@api_bp.route("/posts/<int:post_id>/like", methods=["POST"])
@token_required
def api_like_post(post_id):
    """Like a post."""
    post = db.session.get(Post, post_id)
    if not post:
        return error_response("Post not found", 404)

    if g.current_user.has_liked(post):
        return error_response("Already liked this post", 400)

    g.current_user.like_post(post)

    # Create notification for post author
    if post.author.id != g.current_user.id:
        post.author.add_notification(
            "post_liked",
            {"post_id": post.id, "username": g.current_user.username},
            actor_id=g.current_user.id
        )

    db.session.commit()

    return json_response({
        "message": "Post liked",
        "likes_count": post.likes_count()
    })


@api_bp.route("/posts/<int:post_id>/unlike", methods=["POST"])
@token_required
def api_unlike_post(post_id):
    """Unlike a post."""
    post = db.session.get(Post, post_id)
    if not post:
        return error_response("Post not found", 404)

    if not g.current_user.has_liked(post):
        return error_response("Haven't liked this post", 400)

    g.current_user.unlike_post(post)
    db.session.commit()

    return json_response({
        "message": "Post unliked",
        "likes_count": post.likes_count()
    })


@api_bp.route("/posts/<int:post_id>/comments", methods=["GET"])
@token_required
def api_get_comments(post_id):
    """Get comments on a post."""
    post = db.session.get(Post, post_id)
    if not post:
        return error_response("Post not found", 404)

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    query = post.comments.select().order_by(Comment.timestamp.asc())
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return json_response({
        "comments": [c.to_dict() for c in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    })


@api_bp.route("/posts/<int:post_id>/comments", methods=["POST"])
@token_required
def api_create_comment(post_id):
    """Create a comment on a post."""
    post = db.session.get(Post, post_id)
    if not post:
        return error_response("Post not found", 404)

    data = request.get_json() or {}

    if "body" not in data:
        return error_response("Comment body is required", 400)

    body = data["body"].strip()
    if len(body) < 1 or len(body) > 280:
        return error_response("Comment must be between 1 and 280 characters", 400)

    comment = Comment(body=body, author=g.current_user, post=post)
    db.session.add(comment)

    # Create notification for post author
    if post.author.id != g.current_user.id:
        post.author.add_notification(
            "new_comment",
            {"post_id": post.id, "comment_id": comment.id, "username": g.current_user.username},
            actor_id=g.current_user.id
        )

    db.session.commit()

    return json_response(comment.to_dict(), 201)


@api_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@token_required
def api_delete_comment(comment_id):
    """Delete a comment (only by author or post author)."""
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return error_response("Comment not found", 404)

    if comment.author.id != g.current_user.id and comment.post.author.id != g.current_user.id:
        return error_response("Not authorized to delete this comment", 403)

    db.session.delete(comment)
    db.session.commit()

    return json_response({"message": "Comment deleted"})


@api_bp.route("/search", methods=["GET"])
@token_required
def api_search():
    """
    Search posts and users.

    Query params:
        - q: string (search query)
        - type: string ("posts", "users", or "all")
        - page: int
        - per_page: int
    """
    query = request.args.get("q", "", type=str).strip()
    search_type = request.args.get("type", "all", type=str)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    if not query:
        return error_response("Search query is required", 400)

    results = {}

    if search_type in ["users", "all"]:
        user_query = sa.select(User).where(
            sa.or_(
                User.username.ilike(f"%{query}%"),
                User.about_me.ilike(f"%{query}%")
            )
        ).order_by(User.username)

        if search_type == "users":
            pagination = db.paginate(user_query, page=page, per_page=per_page, error_out=False)
            results = {
                "users": [u.to_dict() for u in pagination.items],
                "total": pagination.total,
                "page": page,
                "per_page": per_page,
                "pages": pagination.pages,
            }
        else:
            users = db.session.scalars(user_query.limit(5)).all()
            results["users"] = [u.to_dict() for u in users]

    if search_type in ["posts", "all"]:
        post_query = sa.select(Post).where(
            Post.body.ilike(f"%{query}%")
        ).order_by(Post.timestamp.desc())

        if search_type == "posts":
            pagination = db.paginate(post_query, page=page, per_page=per_page, error_out=False)
            posts_data = []
            for post in pagination.items:
                post_dict = post.to_dict()
                post_dict["liked"] = g.current_user.has_liked(post)
                posts_data.append(post_dict)
            results = {
                "posts": posts_data,
                "total": pagination.total,
                "page": page,
                "per_page": per_page,
                "pages": pagination.pages,
            }
        else:
            posts = db.session.scalars(post_query.limit(5)).all()
            posts_data = []
            for post in posts:
                post_dict = post.to_dict()
                post_dict["liked"] = g.current_user.has_liked(post)
                posts_data.append(post_dict)
            results["posts"] = posts_data

    return json_response(results)
