"""Async database session configuration with connection pooling."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.config import settings

logger = logging.getLogger(__name__)


def create_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine with optimized settings.

    Uses asyncpg driver for PostgreSQL with connection pooling.
    """
    engine = create_async_engine(
        str(settings.DATABASE_URL),
        # Connection pool settings
        poolclass=AsyncAdaptedQueuePool,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,  # Recycle connections after 1 hour
        # Query logging
        echo=settings.DATABASE_ECHO,
        echo_pool=settings.DEBUG,
        # Connection arguments for asyncpg
        connect_args={
            "server_settings": {
                "application_name": settings.APP_NAME,
                "jit": "off",  # Disable JIT for faster query planning
            },
            "command_timeout": 60,
        },
    )

    # Log pool events in debug mode
    if settings.DEBUG:

        @event.listens_for(engine.sync_engine, "checkout")
        def receive_checkout(
            dbapi_connection: Any, connection_record: Any, connection_proxy: Any
        ) -> None:
            logger.debug("Connection checked out from pool")

        @event.listens_for(engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection: Any, connection_record: Any) -> None:
            logger.debug("Connection returned to pool")

    return engine


# Create engine instance
engine = create_engine()


# Create async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get async database session.

    Provides a session with automatic commit/rollback handling.
    Use with FastAPI's Depends():

    ```python
    @router.get("/users")
    async def get_users(db: AsyncSession = Depends(get_async_session)):
        ...
    ```
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Database error: {e}")
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error during database operation: {e}")
        raise
    finally:
        await session.close()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.

    Use when you need a session outside of FastAPI dependency injection:

    ```python
    async with get_session() as session:
        result = await session.execute(query)
    ```
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        await session.close()


async def check_database_connection() -> bool:
    """
    Check if database is reachable.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def get_pool_status() -> dict[str, Any]:
    """
    Get current connection pool status.

    Returns:
        Dictionary with pool statistics
    """
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalidatedcount(),
    }


async def dispose_engine() -> None:
    """
    Dispose of the engine and all connections.

    Call during application shutdown.
    """
    await engine.dispose()
    logger.info("Database engine disposed")


# Alias for backward compatibility
get_db = get_async_session
