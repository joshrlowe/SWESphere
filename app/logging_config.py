"""Structured logging configuration for SWESphere."""
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from functools import wraps
from logging.handlers import RotatingFileHandler

from flask import g, has_request_context, request


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request context if available
        if has_request_context():
            log_data["request"] = {
                "id": getattr(g, "request_id", None),
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
                "user_agent": str(request.user_agent),
            }

            # Add user info if authenticated
            try:
                from flask_login import current_user
                if current_user.is_authenticated:
                    log_data["user"] = {
                        "id": current_user.id,
                        "username": current_user.username,
                    }
            except Exception:
                pass

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data)


class RequestIDFilter(logging.Filter):
    """Filter that adds request ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if has_request_context():
            record.request_id = getattr(g, "request_id", "-")
        else:
            record.request_id = "-"
        return True


def setup_logging(app):
    """Configure structured logging for the application."""
    # Remove default handlers
    app.logger.handlers = []

    # Create formatters
    if app.config.get("LOG_FORMAT", "json") == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(request_id)s] %(name)s: %(message)s"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestIDFilter())
    console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)
    app.logger.addHandler(console_handler)

    # File handler (rotating)
    import os
    if not os.path.exists("logs"):
        os.mkdir("logs")

    file_handler = RotatingFileHandler(
        "logs/swesphere.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(RequestIDFilter())
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    # Error file handler
    error_handler = RotatingFileHandler(
        "logs/swesphere_errors.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
    )
    error_handler.setFormatter(formatter)
    error_handler.addFilter(RequestIDFilter())
    error_handler.setLevel(logging.ERROR)
    app.logger.addHandler(error_handler)

    # Set log level
    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # Log startup
    app.logger.info("SWESphere logging initialized", extra={
        "extra_data": {"debug_mode": app.debug}
    })


def generate_request_id():
    """Generate a unique request ID."""
    return str(uuid.uuid4())[:8]


def log_request(logger):
    """Decorator to log request start and end."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            logger.info(f"Request started: {f.__name__}")
            try:
                result = f(*args, **kwargs)
                logger.info(f"Request completed: {f.__name__}")
                return result
            except Exception as e:
                logger.exception(f"Request failed: {f.__name__}")
                raise
        return wrapper
    return decorator


class AuditLogger:
    """Logger for security-relevant events."""

    def __init__(self, app):
        self.logger = logging.getLogger("swesphere.audit")
        self.logger.setLevel(logging.INFO)

        # Audit log file
        if not app.debug:
            import os
            if not os.path.exists("logs"):
                os.mkdir("logs")

            handler = RotatingFileHandler(
                "logs/audit.log",
                maxBytes=50 * 1024 * 1024,  # 50MB
                backupCount=30,
            )
            handler.setFormatter(JSONFormatter())
            self.logger.addHandler(handler)

    def log_login_attempt(self, username: str, success: bool, ip: str, reason: str = None):
        """Log login attempt."""
        self.logger.info("Login attempt", extra={
            "extra_data": {
                "event": "login_attempt",
                "username": username,
                "success": success,
                "ip_address": ip,
                "reason": reason,
            }
        })

    def log_password_reset(self, email: str, ip: str):
        """Log password reset request."""
        self.logger.info("Password reset requested", extra={
            "extra_data": {
                "event": "password_reset_request",
                "email": email,
                "ip_address": ip,
            }
        })

    def log_account_lockout(self, username: str, ip: str):
        """Log account lockout."""
        self.logger.warning("Account locked out", extra={
            "extra_data": {
                "event": "account_lockout",
                "username": username,
                "ip_address": ip,
            }
        })

    def log_registration(self, username: str, email: str, ip: str):
        """Log new registration."""
        self.logger.info("New user registration", extra={
            "extra_data": {
                "event": "registration",
                "username": username,
                "email": email,
                "ip_address": ip,
            }
        })
