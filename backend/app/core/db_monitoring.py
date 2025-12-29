"""
Database query monitoring and performance logging.

Provides instrumentation for SQLAlchemy to:
- Log slow queries (>100ms by default)
- Track query execution times
- Monitor connection pool health
- Generate query statistics

Usage:
    from app.core.db_monitoring import setup_query_logging
    setup_query_logging(engine)
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from threading import Lock
from typing import Any, Callable

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

logger = logging.getLogger("app.db.monitoring")

# Default threshold for slow query logging (milliseconds)
SLOW_QUERY_THRESHOLD_MS = 100


@dataclass
class QueryStats:
    """Statistics for tracked queries."""

    total_queries: int = 0
    total_time_ms: float = 0.0
    slow_queries: int = 0
    fastest_query_ms: float = float("inf")
    slowest_query_ms: float = 0.0
    last_slow_query: str | None = None
    last_slow_query_time: datetime | None = None

    # Per-query type stats
    select_count: int = 0
    insert_count: int = 0
    update_count: int = 0
    delete_count: int = 0

    _lock: Lock = field(default_factory=Lock, repr=False)

    def record_query(
        self,
        statement: str,
        duration_ms: float,
        threshold_ms: float,
    ) -> None:
        """Record a query execution."""
        with self._lock:
            self.total_queries += 1
            self.total_time_ms += duration_ms

            if duration_ms < self.fastest_query_ms:
                self.fastest_query_ms = duration_ms

            if duration_ms > self.slowest_query_ms:
                self.slowest_query_ms = duration_ms

            if duration_ms > threshold_ms:
                self.slow_queries += 1
                self.last_slow_query = statement[:500]
                self.last_slow_query_time = datetime.now(timezone.utc)

            # Track query type
            stmt_upper = statement.strip().upper()
            if stmt_upper.startswith("SELECT"):
                self.select_count += 1
            elif stmt_upper.startswith("INSERT"):
                self.insert_count += 1
            elif stmt_upper.startswith("UPDATE"):
                self.update_count += 1
            elif stmt_upper.startswith("DELETE"):
                self.delete_count += 1

    @property
    def avg_query_time_ms(self) -> float:
        """Average query time in milliseconds."""
        if self.total_queries == 0:
            return 0.0
        return self.total_time_ms / self.total_queries

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "total_queries": self.total_queries,
            "total_time_ms": round(self.total_time_ms, 2),
            "avg_query_time_ms": round(self.avg_query_time_ms, 2),
            "slow_queries": self.slow_queries,
            "fastest_query_ms": round(self.fastest_query_ms, 2)
            if self.fastest_query_ms != float("inf")
            else None,
            "slowest_query_ms": round(self.slowest_query_ms, 2),
            "query_counts": {
                "select": self.select_count,
                "insert": self.insert_count,
                "update": self.update_count,
                "delete": self.delete_count,
            },
            "last_slow_query_time": self.last_slow_query_time.isoformat()
            if self.last_slow_query_time
            else None,
        }

    def reset(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self.total_queries = 0
            self.total_time_ms = 0.0
            self.slow_queries = 0
            self.fastest_query_ms = float("inf")
            self.slowest_query_ms = 0.0
            self.last_slow_query = None
            self.last_slow_query_time = None
            self.select_count = 0
            self.insert_count = 0
            self.update_count = 0
            self.delete_count = 0


# Global query statistics
query_stats = QueryStats()


def setup_query_logging(
    engine: Engine,
    threshold_ms: float = SLOW_QUERY_THRESHOLD_MS,
    log_all_queries: bool = False,
) -> None:
    """
    Set up query logging and monitoring for a SQLAlchemy engine.

    Listens to query execution events and logs slow queries.

    Args:
        engine: SQLAlchemy engine to instrument
        threshold_ms: Threshold in ms for slow query logging (default 100)
        log_all_queries: If True, log all queries (not just slow ones)
    """

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        """Record query start time."""
        conn.info.setdefault("query_start_time", []).append(time.perf_counter())

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(
        conn,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        """Log query execution and record statistics."""
        start_times = conn.info.get("query_start_time", [])
        if not start_times:
            return

        start_time = start_times.pop()
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Record in global stats
        query_stats.record_query(statement, duration_ms, threshold_ms)

        # Log based on threshold
        if duration_ms > threshold_ms:
            # Format parameters for logging (truncate long values)
            param_str = _format_parameters(parameters)

            logger.warning(
                "Slow query detected",
                extra={
                    "duration_ms": round(duration_ms, 2),
                    "threshold_ms": threshold_ms,
                    "statement": _truncate_statement(statement),
                    "parameters": param_str,
                    "executemany": executemany,
                },
            )
        elif log_all_queries:
            logger.debug(
                "Query executed",
                extra={
                    "duration_ms": round(duration_ms, 2),
                    "statement": _truncate_statement(statement, max_length=100),
                },
            )

    @event.listens_for(engine, "handle_error")
    def handle_error(exception_context):
        """Log database errors."""
        logger.error(
            "Database error",
            extra={
                "error": str(exception_context.original_exception),
                "statement": _truncate_statement(
                    exception_context.statement or "Unknown"
                ),
            },
            exc_info=exception_context.original_exception,
        )

    logger.info(f"Query logging enabled with {threshold_ms}ms threshold")


def setup_pool_monitoring(engine: Engine) -> None:
    """
    Set up connection pool monitoring.

    Logs pool checkout/checkin events and connection issues.

    Args:
        engine: SQLAlchemy engine to monitor
    """
    pool = engine.pool

    @event.listens_for(pool, "checkout")
    def on_checkout(dbapi_connection, connection_record, connection_proxy):
        """Log connection checkout."""
        logger.debug(
            "Connection checked out from pool",
            extra={"pool_size": pool.size(), "checked_out": pool.checkedout()},
        )

    @event.listens_for(pool, "checkin")
    def on_checkin(dbapi_connection, connection_record):
        """Log connection checkin."""
        logger.debug(
            "Connection returned to pool",
            extra={"pool_size": pool.size(), "checked_out": pool.checkedout()},
        )

    @event.listens_for(pool, "connect")
    def on_connect(dbapi_connection, connection_record):
        """Log new connection creation."""
        logger.info("New database connection created")

    @event.listens_for(pool, "invalidate")
    def on_invalidate(dbapi_connection, connection_record, exception):
        """Log connection invalidation."""
        logger.warning(
            "Database connection invalidated",
            extra={"error": str(exception) if exception else None},
        )

    logger.info("Connection pool monitoring enabled")


def _truncate_statement(statement: str, max_length: int = 500) -> str:
    """Truncate SQL statement for logging."""
    statement = " ".join(statement.split())  # Normalize whitespace
    if len(statement) > max_length:
        return statement[:max_length] + "..."
    return statement


def _format_parameters(parameters: Any, max_length: int = 200) -> str:
    """Format query parameters for logging."""
    if parameters is None:
        return "None"

    try:
        param_str = str(parameters)
        if len(param_str) > max_length:
            return param_str[:max_length] + "..."
        return param_str
    except Exception:
        return "<unable to format parameters>"


@contextmanager
def query_timer(operation_name: str):
    """
    Context manager for timing database operations.

    Usage:
        with query_timer("fetch_user_feed"):
            posts = await repo.get_home_feed(user_id)

    Args:
        operation_name: Name for logging
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            f"Database operation completed",
            extra={
                "operation": operation_name,
                "duration_ms": round(duration_ms, 2),
            },
        )


def log_query_stats() -> None:
    """Log current query statistics."""
    stats = query_stats.to_dict()
    logger.info(
        "Query statistics",
        extra={
            "stats": stats,
            "total_queries": stats["total_queries"],
            "slow_queries": stats["slow_queries"],
            "avg_time_ms": stats["avg_query_time_ms"],
        },
    )


def get_query_stats() -> dict[str, Any]:
    """Get current query statistics as dictionary."""
    return query_stats.to_dict()


def reset_query_stats() -> None:
    """Reset query statistics."""
    query_stats.reset()
    logger.info("Query statistics reset")


# Decorator for timing async functions
def timed_query(func: Callable) -> Callable:
    """
    Decorator to time and log async database functions.

    Usage:
        @timed_query
        async def get_user(user_id: int):
            ...
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            if duration_ms > SLOW_QUERY_THRESHOLD_MS:
                logger.warning(
                    f"Slow database operation: {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "duration_ms": round(duration_ms, 2),
                    },
                )
            else:
                logger.debug(
                    f"Database operation: {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "duration_ms": round(duration_ms, 2),
                    },
                )

    return wrapper

