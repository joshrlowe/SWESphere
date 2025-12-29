"""Application configuration."""

from dotenv import load_dotenv
import os

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv()


class Config:
    """Base configuration."""

    # Admin emails
    ADMINS = os.environ.get("ADMINS", "").split(",")

    # Supported languages
    LANGUAGES = [
        "en",
        "es",
        "fr",
        "de",
        "it",
        "pt",
        "ru",
        "zh",
        "ja",
        "ko",
        "ar",
        "hi",
        "pl",
    ]

    # Pagination
    POSTS_PER_PAGE = 25
    COMMENTS_PER_PAGE = 10
    NOTIFICATIONS_PER_PAGE = 20

    # Security
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL"
    ) or "sqlite:///" + os.path.join(basedir, "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 25)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS") == "True"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    # Session security
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = "__Host-session"

    # Rate limiting
    RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "True") == "True"
    RATELIMIT_STORAGE_URL = os.environ.get("REDIS_URL", "memory://")
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    RATELIMIT_HEADERS_ENABLED = True

    # Login rate limits
    LOGIN_RATE_LIMIT = "5 per minute"
    REGISTER_RATE_LIMIT = "3 per hour"
    PASSWORD_RESET_RATE_LIMIT = "3 per hour"

    # Account lockout
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    LOCKOUT_PROGRESSIVE = True  # Double lockout time on each subsequent lockout

    # Password requirements
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = False

    # File uploads
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB
    AVATAR_SIZE = (256, 256)  # Width, Height

    # Email verification
    EMAIL_VERIFICATION_REQUIRED = (
        os.environ.get("EMAIL_VERIFICATION_REQUIRED", "False") == "True"
    )
    EMAIL_VERIFICATION_EXPIRY = 24 * 60 * 60  # 24 hours

    # JWT tokens
    PASSWORD_RESET_EXPIRY = 600  # 10 minutes
    API_TOKEN_EXPIRY = 24 * 60 * 60  # 24 hours

    # Logging
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "json")  # "json" or "text"

    # Real-time
    SOCKETIO_MESSAGE_QUEUE = os.environ.get("REDIS_URL")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False
    EMAIL_VERIFICATION_REQUIRED = False
    LOG_FORMAT = "text"


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    EMAIL_VERIFICATION_REQUIRED = False


class ProductionConfig(Config):
    """Production configuration."""

    pass


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": Config,
}
