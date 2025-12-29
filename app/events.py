"""WebSocket event handlers for real-time features."""

from flask import g
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room

try:
    from app import socketio, db
    from app.models import Notification

    @socketio.on("connect")
    def handle_connect():
        """Handle client connection."""
        if current_user.is_authenticated:
            # Join user's personal room for notifications
            join_room(f"user_{current_user.id}")
            emit("connected", {"user_id": current_user.id})

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle client disconnection."""
        if current_user.is_authenticated:
            leave_room(f"user_{current_user.id}")

    @socketio.on("subscribe_post")
    def handle_subscribe_post(data):
        """Subscribe to updates for a specific post."""
        post_id = data.get("post_id")
        if post_id:
            join_room(f"post_{post_id}")

    @socketio.on("unsubscribe_post")
    def handle_unsubscribe_post(data):
        """Unsubscribe from post updates."""
        post_id = data.get("post_id")
        if post_id:
            leave_room(f"post_{post_id}")

    @socketio.on("mark_notification_read")
    def handle_mark_read(data):
        """Mark a notification as read via WebSocket."""
        if not current_user.is_authenticated:
            return

        notification_id = data.get("notification_id")
        if notification_id:
            notification = db.session.get(Notification, notification_id)
            if notification and notification.user_id == current_user.id:
                notification.read = True
                db.session.commit()
                emit("notification_read", {"notification_id": notification_id})

    def send_notification(user_id: int, notification_data: dict):
        """Send a notification to a specific user via WebSocket."""
        socketio.emit("new_notification", notification_data, room=f"user_{user_id}")

    def send_post_update(post_id: int, update_type: str, data: dict):
        """Send an update about a post to all subscribers."""
        socketio.emit(
            "post_update",
            {"type": update_type, "post_id": post_id, **data},
            room=f"post_{post_id}",
        )

except ImportError:
    # Flask-SocketIO not installed
    def send_notification(user_id: int, notification_data: dict):
        """No-op when SocketIO is not available."""
        pass

    def send_post_update(post_id: int, update_type: str, data: dict):
        """No-op when SocketIO is not available."""
        pass
