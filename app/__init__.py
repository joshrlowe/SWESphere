"""Flask application factory and extensions."""
from config import Config
from flask import Flask, g, request
from flask_babel import Babel, lazy_gettext as _l
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import os
import uuid


def get_locale():
    return request.accept_languages.best_match(app.config["LANGUAGES"])


app = Flask(__name__)
app.config.from_object(Config)

# Database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Authentication
login = LoginManager(app)
login.login_view = "login"
login.login_message = _l("Please log in to access this page.")

# Email
mail = Mail(app)

# Internationalization
babel = Babel(app, locale_selector=get_locale)

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=app.config.get("RATELIMIT_STORAGE_URL", "memory://"),
    enabled=app.config.get("RATELIMIT_ENABLED", True),
)


# Request ID middleware
@app.before_request
def add_request_id():
    """Add unique request ID for logging correlation."""
    g.request_id = str(uuid.uuid4())[:8]


# Setup logging
from app.logging_config import setup_logging, AuditLogger

if not app.debug or os.environ.get("FORCE_LOGGING"):
    setup_logging(app)

# Audit logger for security events
audit_logger = AuditLogger(app)

# Create upload directories
upload_folder = app.config.get("UPLOAD_FOLDER", "uploads")
avatar_folder = os.path.join(upload_folder, "avatars")
for folder in [upload_folder, avatar_folder]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Import routes and models
from app import routes, models, errors

# Register API blueprint
try:
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api/v1")
except ImportError:
    pass  # API module not yet created

# SocketIO for real-time features (optional)
socketio = None
try:
    from flask_socketio import SocketIO
    socketio = SocketIO(
        app,
        message_queue=app.config.get("SOCKETIO_MESSAGE_QUEUE"),
        cors_allowed_origins="*"
    )
    from app import events  # Import socket event handlers
except ImportError:
    app.logger.info("Flask-SocketIO not available, real-time features disabled")
except Exception:
    pass
