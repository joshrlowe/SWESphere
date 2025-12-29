"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    PostgresDsn,
    RedisDsn,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Environment variables can be set directly or via a .env file.
    All settings have sensible defaults for development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===================
    # Application
    # ===================
    APP_NAME: str = "SWESphere"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ===================
    # Server
    # ===================
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = False

    # ===================
    # Security / JWT
    # ===================
    SECRET_KEY: SecretStr = SecretStr("change-me-in-production-use-secrets-manager")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password requirements
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True

    # ===================
    # Database (PostgreSQL)
    # ===================
    DATABASE_URL: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/swesphere"
    )
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False  # Log SQL queries

    # ===================
    # Redis
    # ===================
    REDIS_URL: RedisDsn = RedisDsn("redis://localhost:6379/0")
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    REDIS_TOKEN_BLACKLIST_PREFIX: str = "token_blacklist:"

    # ===================
    # Celery
    # ===================
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_ALWAYS_EAGER: bool = False  # True for testing

    # ===================
    # CORS
    # ===================
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",      # SvelteKit default
        "http://localhost:5173",      # Vite/SvelteKit dev
        "http://localhost:4173",      # Vite preview
        "http://127.0.0.1:5173",
        "capacitor://localhost",      # Mobile (Capacitor)
        "ionic://localhost",          # Mobile (Ionic)
        "http://localhost",           # Flutter web
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from JSON string or list."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Comma-separated string
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ===================
    # Rate Limiting
    # ===================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_ANONYMOUS: str = "30/minute"
    RATE_LIMIT_AUTHENTICATED: str = "60/minute"
    RATE_LIMIT_STORAGE: str = "redis://localhost:6379/3"

    # ===================
    # File Uploads
    # ===================
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    UPLOAD_DIR: Path = Path("uploads")
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    AVATAR_MAX_SIZE: int = 2 * 1024 * 1024  # 2MB

    # ===================
    # Email
    # ===================
    MAIL_ENABLED: bool = False
    MAIL_SERVER: str | None = None
    MAIL_PORT: int = 587
    MAIL_USE_TLS: bool = True
    MAIL_USE_SSL: bool = False
    MAIL_USERNAME: str | None = None
    MAIL_PASSWORD: SecretStr | None = None
    MAIL_FROM: str = "noreply@swesphere.com"
    MAIL_FROM_NAME: str = "SWESphere"

    # ===================
    # Pagination
    # ===================
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # ===================
    # Posts
    # ===================
    POST_MAX_LENGTH: int = 280
    COMMENT_MAX_LENGTH: int = 500

    # ===================
    # Computed Properties
    # ===================

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.APP_ENV == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in test mode (Celery eager)."""
        return self.CELERY_TASK_ALWAYS_EAGER

    @property
    def jwt_secret_key(self) -> str:
        """Get the JWT secret key as a string."""
        return self.SECRET_KEY.get_secret_value()

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (for Alembic)."""
        return str(self.DATABASE_URL).replace("+asyncpg", "")

    # ===================
    # Validators
    # ===================

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate that production has proper security settings."""
        if self.is_production:
            # Ensure secret key is changed
            if "change-me" in self.SECRET_KEY.get_secret_value():
                raise ValueError(
                    "SECRET_KEY must be changed in production! "
                    "Use: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            
            # Ensure debug is off
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
        
        return self

    @field_validator("UPLOAD_DIR", mode="after")
    @classmethod
    def create_upload_dir(cls, v: Path) -> Path:
        """Ensure upload directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        (v / "avatars").mkdir(exist_ok=True)
        (v / "media").mkdir(exist_ok=True)
        return v


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
