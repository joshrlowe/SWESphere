"""
Tests for database query monitoring module.

Tests cover:
- QueryStats tracking
- Slow query detection
- Query timing utilities
- Statistics reset and retrieval
"""

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.db_monitoring import (
    QueryStats,
    SLOW_QUERY_THRESHOLD_MS,
    get_query_stats,
    log_query_stats,
    query_stats,
    query_timer,
    reset_query_stats,
    setup_pool_monitoring,
    setup_query_logging,
    timed_query,
)


# =============================================================================
# QueryStats Tests
# =============================================================================


class TestQueryStats:
    """Tests for QueryStats dataclass."""

    def test_initial_state(self):
        """Test QueryStats initial values."""
        stats = QueryStats()

        assert stats.total_queries == 0
        assert stats.total_time_ms == 0.0
        assert stats.slow_queries == 0
        assert stats.fastest_query_ms == float("inf")
        assert stats.slowest_query_ms == 0.0
        assert stats.last_slow_query is None
        assert stats.last_slow_query_time is None
        assert stats.select_count == 0
        assert stats.insert_count == 0
        assert stats.update_count == 0
        assert stats.delete_count == 0

    def test_record_query_basic(self):
        """Test recording a basic query."""
        stats = QueryStats()

        stats.record_query("SELECT * FROM users", 50.0, 100.0)

        assert stats.total_queries == 1
        assert stats.total_time_ms == 50.0
        assert stats.slow_queries == 0
        assert stats.fastest_query_ms == 50.0
        assert stats.slowest_query_ms == 50.0
        assert stats.select_count == 1

    def test_record_slow_query(self):
        """Test recording a slow query."""
        stats = QueryStats()

        stats.record_query("SELECT * FROM posts", 150.0, 100.0)

        assert stats.slow_queries == 1
        assert stats.last_slow_query is not None
        assert "SELECT" in stats.last_slow_query
        assert stats.last_slow_query_time is not None

    def test_record_multiple_queries(self):
        """Test recording multiple queries."""
        stats = QueryStats()

        stats.record_query("SELECT * FROM users", 10.0, 100.0)
        stats.record_query("INSERT INTO posts VALUES ...", 20.0, 100.0)
        stats.record_query("UPDATE users SET ...", 30.0, 100.0)
        stats.record_query("DELETE FROM comments WHERE ...", 40.0, 100.0)

        assert stats.total_queries == 4
        assert stats.total_time_ms == 100.0
        assert stats.fastest_query_ms == 10.0
        assert stats.slowest_query_ms == 40.0
        assert stats.select_count == 1
        assert stats.insert_count == 1
        assert stats.update_count == 1
        assert stats.delete_count == 1

    def test_record_query_updates_min_max(self):
        """Test that min/max times are tracked correctly."""
        stats = QueryStats()

        stats.record_query("SELECT 1", 50.0, 100.0)
        assert stats.fastest_query_ms == 50.0
        assert stats.slowest_query_ms == 50.0

        stats.record_query("SELECT 2", 10.0, 100.0)
        assert stats.fastest_query_ms == 10.0
        assert stats.slowest_query_ms == 50.0

        stats.record_query("SELECT 3", 100.0, 200.0)
        assert stats.fastest_query_ms == 10.0
        assert stats.slowest_query_ms == 100.0

    def test_avg_query_time_calculation(self):
        """Test average query time property."""
        stats = QueryStats()

        stats.record_query("SELECT 1", 10.0, 100.0)
        stats.record_query("SELECT 2", 20.0, 100.0)
        stats.record_query("SELECT 3", 30.0, 100.0)

        assert stats.avg_query_time_ms == 20.0

    def test_avg_query_time_zero_queries(self):
        """Test average with no queries."""
        stats = QueryStats()

        assert stats.avg_query_time_ms == 0.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = QueryStats()
        stats.record_query("SELECT * FROM users", 50.0, 100.0)
        stats.record_query("INSERT INTO posts", 150.0, 100.0)  # Slow

        result = stats.to_dict()

        assert result["total_queries"] == 2
        assert result["total_time_ms"] == 200.0
        assert result["avg_query_time_ms"] == 100.0
        assert result["slow_queries"] == 1
        assert result["fastest_query_ms"] == 50.0
        assert result["slowest_query_ms"] == 150.0
        assert result["query_counts"]["select"] == 1
        assert result["query_counts"]["insert"] == 1
        assert result["last_slow_query_time"] is not None

    def test_reset(self):
        """Test resetting statistics."""
        stats = QueryStats()
        stats.record_query("SELECT * FROM users", 150.0, 100.0)
        stats.record_query("INSERT INTO posts", 50.0, 100.0)

        stats.reset()

        assert stats.total_queries == 0
        assert stats.total_time_ms == 0.0
        assert stats.slow_queries == 0
        assert stats.fastest_query_ms == float("inf")
        assert stats.slowest_query_ms == 0.0
        assert stats.last_slow_query is None
        assert stats.select_count == 0

    def test_long_statement_truncation(self):
        """Test that long SQL statements are truncated."""
        stats = QueryStats()

        long_sql = "SELECT " + "a, " * 500 + "FROM table"
        stats.record_query(long_sql, 150.0, 100.0)

        assert len(stats.last_slow_query) <= 500

    def test_thread_safety(self):
        """Test that recording is thread-safe."""
        stats = QueryStats()

        def record_many():
            for _ in range(100):
                stats.record_query("SELECT 1", 10.0, 100.0)

        import threading

        threads = [threading.Thread(target=record_many) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert stats.total_queries == 1000

    def test_query_type_detection_case_insensitive(self):
        """Test query type detection is case-insensitive."""
        stats = QueryStats()

        stats.record_query("select * from users", 10.0, 100.0)
        stats.record_query("SELECT * from users", 10.0, 100.0)
        stats.record_query("  SELECT * from users", 10.0, 100.0)

        assert stats.select_count == 3


# =============================================================================
# Global Stats Functions Tests
# =============================================================================


class TestGlobalStatsFunctions:
    """Tests for global statistics functions."""

    def setup_method(self):
        """Reset stats before each test."""
        reset_query_stats()

    def teardown_method(self):
        """Clean up after each test."""
        reset_query_stats()

    def test_get_query_stats(self):
        """Test getting global query stats."""
        query_stats.record_query("SELECT 1", 50.0, 100.0)

        stats = get_query_stats()

        assert isinstance(stats, dict)
        assert stats["total_queries"] == 1

    def test_reset_query_stats(self):
        """Test resetting global query stats."""
        query_stats.record_query("SELECT 1", 50.0, 100.0)

        reset_query_stats()

        stats = get_query_stats()
        assert stats["total_queries"] == 0

    def test_log_query_stats(self):
        """Test logging query stats."""
        query_stats.record_query("SELECT 1", 50.0, 100.0)

        # Should not raise
        with patch("app.core.db_monitoring.logger") as mock_logger:
            log_query_stats()
            mock_logger.info.assert_called_once()


# =============================================================================
# query_timer Context Manager Tests
# =============================================================================


class TestQueryTimer:
    """Tests for query_timer context manager."""

    def test_query_timer_logs_operation(self):
        """Test that query_timer logs the operation."""
        with patch("app.core.db_monitoring.logger") as mock_logger:
            with query_timer("test_operation"):
                time.sleep(0.01)  # 10ms

            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args
            assert "test_operation" in str(call_args)

    def test_query_timer_measures_time(self):
        """Test that query_timer measures elapsed time."""
        with patch("app.core.db_monitoring.logger") as mock_logger:
            with query_timer("sleep_test"):
                time.sleep(0.05)  # 50ms

            call_kwargs = mock_logger.debug.call_args[1]
            extra = call_kwargs.get("extra", {})
            duration = extra.get("duration_ms", 0)

            assert duration >= 40  # At least 40ms (with some tolerance)

    def test_query_timer_handles_exception(self):
        """Test that query_timer still logs on exception."""
        with patch("app.core.db_monitoring.logger") as mock_logger:
            with pytest.raises(ValueError):
                with query_timer("error_test"):
                    raise ValueError("Test error")

            # Should still have logged
            mock_logger.debug.assert_called_once()


# =============================================================================
# timed_query Decorator Tests
# =============================================================================


class TestTimedQueryDecorator:
    """Tests for timed_query async decorator."""

    @pytest.mark.asyncio
    async def test_timed_query_logs_execution(self):
        """Test that timed_query decorator logs function execution."""

        @timed_query
        async def sample_function():
            await asyncio.sleep(0.01)
            return "result"

        with patch("app.core.db_monitoring.logger") as mock_logger:
            result = await sample_function()

            assert result == "result"
            # Should log debug for fast queries
            assert mock_logger.debug.called or mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_timed_query_slow_function(self):
        """Test that slow functions trigger warning."""

        @timed_query
        async def slow_function():
            await asyncio.sleep(0.15)  # 150ms > 100ms threshold
            return "done"

        with patch("app.core.db_monitoring.logger") as mock_logger:
            result = await slow_function()

            assert result == "done"
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_timed_query_preserves_function_name(self):
        """Test that decorator preserves function name."""

        @timed_query
        async def my_custom_function():
            return True

        assert my_custom_function.__name__ == "my_custom_function"

    @pytest.mark.asyncio
    async def test_timed_query_with_arguments(self):
        """Test decorator with function arguments."""

        @timed_query
        async def add_numbers(a: int, b: int) -> int:
            return a + b

        result = await add_numbers(5, 3)
        assert result == 8

    @pytest.mark.asyncio
    async def test_timed_query_with_kwargs(self):
        """Test decorator with keyword arguments."""

        @timed_query
        async def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        result = await greet("World", greeting="Hi")
        assert result == "Hi, World!"

    @pytest.mark.asyncio
    async def test_timed_query_logs_on_exception(self):
        """Test that decorator logs even on exception."""

        @timed_query
        async def failing_function():
            raise RuntimeError("Test failure")

        with patch("app.core.db_monitoring.logger") as mock_logger:
            with pytest.raises(RuntimeError):
                await failing_function()

            # Should still log
            assert mock_logger.debug.called or mock_logger.warning.called


# =============================================================================
# setup_query_logging Tests
# =============================================================================


class TestSetupQueryLogging:
    """Tests for setup_query_logging function."""

    def test_setup_registers_event_listeners(self):
        """Test that setup registers SQLAlchemy event listeners."""
        mock_engine = MagicMock()

        with patch("app.core.db_monitoring.event") as mock_event:
            setup_query_logging(mock_engine, threshold_ms=100.0)

            # Should register before and after cursor execute
            assert mock_event.listens_for.call_count >= 2

    def test_setup_with_custom_threshold(self):
        """Test setup with custom threshold."""
        mock_engine = MagicMock()

        with patch("app.core.db_monitoring.event"):
            with patch("app.core.db_monitoring.logger") as mock_logger:
                setup_query_logging(mock_engine, threshold_ms=50.0)

                mock_logger.info.assert_called()
                call_args = str(mock_logger.info.call_args)
                assert "50" in call_args

    def test_setup_log_all_queries_option(self):
        """Test setup with log_all_queries enabled."""
        mock_engine = MagicMock()

        with patch("app.core.db_monitoring.event"):
            # Should not raise
            setup_query_logging(mock_engine, log_all_queries=True)


# =============================================================================
# setup_pool_monitoring Tests
# =============================================================================


class TestSetupPoolMonitoring:
    """Tests for setup_pool_monitoring function."""

    def test_setup_registers_pool_listeners(self):
        """Test that setup registers pool event listeners."""
        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_engine.pool = mock_pool

        with patch("app.core.db_monitoring.event") as mock_event:
            setup_pool_monitoring(mock_engine)

            # Should register checkout, checkin, connect, invalidate
            assert mock_event.listens_for.call_count >= 4


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for db_monitoring."""

    def setup_method(self):
        """Reset stats before each test."""
        reset_query_stats()

    def teardown_method(self):
        """Clean up after each test."""
        reset_query_stats()

    def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow."""
        # Record some queries
        query_stats.record_query("SELECT * FROM users", 50.0, 100.0)
        query_stats.record_query("INSERT INTO posts VALUES (...)", 75.0, 100.0)
        query_stats.record_query("SELECT * FROM posts WHERE id = ?", 150.0, 100.0)

        # Get stats
        stats = get_query_stats()

        assert stats["total_queries"] == 3
        assert stats["slow_queries"] == 1
        assert stats["query_counts"]["select"] == 2
        assert stats["query_counts"]["insert"] == 1

        # Reset and verify
        reset_query_stats()
        stats = get_query_stats()
        assert stats["total_queries"] == 0

    def test_threshold_constant(self):
        """Test that threshold constant is accessible."""
        assert SLOW_QUERY_THRESHOLD_MS == 100

    @pytest.mark.asyncio
    async def test_decorator_with_real_async_work(self):
        """Test decorator with realistic async operations."""

        @timed_query
        async def simulate_db_query():
            await asyncio.sleep(0.02)  # Simulate 20ms query
            return {"id": 1, "name": "Test"}

        result = await simulate_db_query()

        assert result == {"id": 1, "name": "Test"}

    def test_stats_accuracy_under_load(self):
        """Test stats accuracy with many queries."""
        reset_query_stats()

        for i in range(1000):
            duration = (i % 10) * 20.0  # 0, 20, 40, ..., 180ms
            query_stats.record_query(f"SELECT {i}", duration, 100.0)

        stats = get_query_stats()

        assert stats["total_queries"] == 1000
        # 8 out of 10 patterns are > 100ms (120, 140, 160, 180, 0+100=no, etc)
        # Actually: 0, 20, 40, 60, 80 < 100; 100 is not >, but 120, 140, 160, 180 are
        # So 4 patterns (120, 140, 160, 180) per 10 = 40%
        expected_slow = 400
        assert stats["slow_queries"] == expected_slow


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_statement(self):
        """Test handling empty SQL statement."""
        stats = QueryStats()

        stats.record_query("", 10.0, 100.0)

        assert stats.total_queries == 1
        # Empty statement shouldn't match any query type
        assert stats.select_count == 0

    def test_very_fast_query(self):
        """Test handling very fast queries."""
        stats = QueryStats()

        stats.record_query("SELECT 1", 0.001, 100.0)

        assert stats.fastest_query_ms == 0.001

    def test_very_slow_query(self):
        """Test handling very slow queries."""
        stats = QueryStats()

        stats.record_query("SELECT * FROM huge_table", 999999.0, 100.0)

        assert stats.slowest_query_ms == 999999.0
        assert stats.slow_queries == 1

    def test_null_threshold(self):
        """Test with zero threshold (all queries are slow)."""
        stats = QueryStats()

        stats.record_query("SELECT 1", 0.1, 0.0)

        assert stats.slow_queries == 1

    def test_whitespace_statement(self):
        """Test statement with leading/trailing whitespace."""
        stats = QueryStats()

        stats.record_query("  SELECT * FROM users  ", 10.0, 100.0)

        assert stats.select_count == 1

