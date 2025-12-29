"""
Application lifecycle event handlers.

Manages startup and shutdown tasks including:
- Database connection pool initialization
- Redis connection management
- WebSocket connection manager initialization
- Upload directory creation
"""

import logging
from pathlib import Path

from app.config import settings
from app.core.websocket import connection_manager
from app.db.session import engine
from app.dependencies import get_redis, close_redis

logger = logging.getLogger(__name__)


async def on_startup() -> None:
    """
    Execute initialization tasks on application startup.

    Tasks performed:
    1. Log startup information
    2. Verify database connection pool
    3. Establish Redis connection
    4. Initialize WebSocket connection manager
    5. Create required directories
    """
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")

    # Database pool is initialized on import, just log confirmation
    logger.info("Database connection pool initialized")

    # Initialize and verify Redis connection
    redis = await _initialize_redis()

    # Initialize WebSocket connection manager with Redis
    await _initialize_websocket_manager(redis)

    # Ensure upload directories exist
    _create_upload_directories()

    logger.info(f"{settings.APP_NAME} started successfully")


async def on_shutdown() -> None:
    """
    Execute cleanup tasks on application shutdown.

    Tasks performed:
    1. Close WebSocket connections
    2. Close database connection pool
    3. Close Redis connection
    """
    logger.info(f"Shutting down {settings.APP_NAME}")

    # Shutdown WebSocket manager first (gracefully close connections)
    await connection_manager.shutdown()
    logger.info("WebSocket connections closed")

    # Dispose database engine and close all connections
    await engine.dispose()
    logger.info("Database connections closed")

    # Close Redis connection
    await close_redis()
    logger.info("Redis connection closed")

    logger.info(f"{settings.APP_NAME} shutdown complete")


async def _initialize_redis():
    """Initialize Redis connection and verify connectivity."""
    from redis.asyncio import Redis
    
    try:
        redis: Redis = await get_redis()
        await redis.ping()
        logger.info("Redis connection established")
        return redis
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def _initialize_websocket_manager(redis) -> None:
    """Initialize WebSocket connection manager with Redis for pub/sub."""
    try:
        await connection_manager.startup(redis)
        logger.info("WebSocket connection manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket manager: {e}")
        raise


def _create_upload_directories() -> None:
    """Create required upload directories if they don't exist."""
    upload_path = Path(settings.UPLOAD_DIR)

    directories = [
        upload_path,
        upload_path / "avatars",
        upload_path / "media",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    logger.info(f"Upload directories verified at {upload_path}")
