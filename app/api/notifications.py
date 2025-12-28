"""API Notification endpoints."""
from app import db
from app.api import api_bp, json_response, error_response, token_required
from app.models import Notification
from flask import request, g
import sqlalchemy as sa


@api_bp.route("/notifications", methods=["GET"])
@token_required
def api_get_notifications():
    """
    Get user notifications.

    Query params:
        - page: int (default 1)
        - per_page: int (default 20, max 100)
        - unread_only: bool (default false)
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    unread_only = request.args.get("unread_only", "false").lower() == "true"

    query = g.current_user.notifications.select().order_by(Notification.timestamp.desc())

    if unread_only:
        query = query.where(Notification.read == False)

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)

    return json_response({
        "notifications": [n.to_dict() for n in pagination.items],
        "total": pagination.total,
        "unread_count": g.current_user.unread_notification_count(),
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    })


@api_bp.route("/notifications/unread-count", methods=["GET"])
@token_required
def api_unread_count():
    """Get count of unread notifications."""
    return json_response({
        "unread_count": g.current_user.unread_notification_count()
    })


@api_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@token_required
def api_mark_notification_read(notification_id):
    """Mark a notification as read."""
    notification = db.session.get(Notification, notification_id)

    if not notification:
        return error_response("Notification not found", 404)

    if notification.user_id != g.current_user.id:
        return error_response("Not authorized", 403)

    notification.read = True
    db.session.commit()

    return json_response({"message": "Notification marked as read"})


@api_bp.route("/notifications/read-all", methods=["POST"])
@token_required
def api_mark_all_read():
    """Mark all notifications as read."""
    db.session.execute(
        sa.update(Notification)
        .where(Notification.user_id == g.current_user.id)
        .where(Notification.read == False)
        .values(read=True)
    )
    db.session.commit()

    return json_response({"message": "All notifications marked as read"})


@api_bp.route("/notifications/<int:notification_id>", methods=["DELETE"])
@token_required
def api_delete_notification(notification_id):
    """Delete a notification."""
    notification = db.session.get(Notification, notification_id)

    if not notification:
        return error_response("Notification not found", 404)

    if notification.user_id != g.current_user.id:
        return error_response("Not authorized", 403)

    db.session.delete(notification)
    db.session.commit()

    return json_response({"message": "Notification deleted"})
