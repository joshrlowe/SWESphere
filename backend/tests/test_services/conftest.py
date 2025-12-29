"""
Test fixtures for service tests.

Provides mock repositories and Redis for isolated service testing.
"""

from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.user import User
from app.models.post import Post
from app.models.notification import Notification, NotificationType
from app.repositories.user_repository import UserRepository
from app.repositories.post_repository import PostRepository
from app.services.cache_service import CacheService
from app.services.cache_invalidation import CacheInvalidator


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    """Create async engine for tests with proper cleanup."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # StaticPool keeps the same connection for in-memory SQLite
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for tests."""
    async_session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest_asyncio.fixture
async def user_repo(db_session: AsyncSession) -> UserRepository:
    """Create user repository."""
    return UserRepository(db_session)


@pytest_asyncio.fixture
async def post_repo(db_session: AsyncSession) -> PostRepository:
    """Create post repository."""
    return PostRepository(db_session)


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=False)
    redis.incr = AsyncMock(return_value=1)
    redis.decr = AsyncMock(return_value=0)
    redis.publish = AsyncMock(return_value=1)
    redis.scan_iter = MagicMock(return_value=iter([]))
    return redis


@pytest_asyncio.fixture
async def user_factory(db_session: AsyncSession):
    """Factory for creating test users."""
    counter = 0

    async def _create_user(**kwargs: Any) -> User:
        nonlocal counter
        counter += 1

        defaults = {
            "username": f"testuser{counter}",
            "email": f"test{counter}@example.com",
            "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VBCvZ/0LIqnPGy",  # "password"
            "is_active": True,
            "failed_login_attempts": 0,
            "locked_until": None,
        }
        defaults.update(kwargs)

        user = User(**defaults)
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    return _create_user


@pytest_asyncio.fixture
async def post_factory(db_session: AsyncSession, user_factory):
    """Factory for creating test posts."""
    counter = 0

    async def _create_post(author: User | None = None, **kwargs: Any) -> Post:
        nonlocal counter
        counter += 1

        if author is None:
            author = await user_factory()

        defaults = {
            "user_id": author.id,
            "body": f"Test post content {counter}",
        }
        defaults.update(kwargs)

        post = Post(**defaults)
        db_session.add(post)
        await db_session.flush()
        await db_session.refresh(post)
        return post

    return _create_post


# =============================================================================
# Cache Service Fixtures
# =============================================================================


@pytest.fixture
def mock_redis_full():
    """Create a more complete mock Redis client for cache testing."""
    redis = AsyncMock()
    
    # Storage for simulating Redis behavior
    _storage: dict[str, Any] = {}
    _sets: dict[str, set] = {}
    _lists: dict[str, list] = {}
    _hashes: dict[str, dict] = {}
    
    async def mock_get(key: str):
        return _storage.get(key)
    
    async def mock_set(key: str, value: str, *args, **kwargs):
        _storage[key] = value
        return True
    
    async def mock_setex(key: str, ttl: int, value: str):
        _storage[key] = value
        return True
    
    async def mock_delete(*keys: str):
        count = 0
        for key in keys:
            if key in _storage:
                del _storage[key]
                count += 1
            if key in _sets:
                del _sets[key]
                count += 1
            if key in _lists:
                del _lists[key]
                count += 1
        return count
    
    async def mock_exists(*keys: str):
        return sum(1 for k in keys if k in _storage or k in _sets or k in _lists)
    
    async def mock_expire(key: str, ttl: int):
        return key in _storage or key in _sets or key in _lists
    
    async def mock_incr(key: str):
        _storage[key] = str(int(_storage.get(key, "0")) + 1)
        return int(_storage[key])
    
    async def mock_incrby(key: str, amount: int):
        _storage[key] = str(int(_storage.get(key, "0")) + amount)
        return int(_storage[key])
    
    async def mock_decr(key: str):
        current = int(_storage.get(key, "0"))
        new_val = max(0, current - 1)
        _storage[key] = str(new_val)
        return new_val
    
    async def mock_decrby(key: str, amount: int):
        current = int(_storage.get(key, "0"))
        new_val = current - amount
        _storage[key] = str(new_val)
        return new_val
    
    # List operations
    async def mock_lrange(key: str, start: int, end: int):
        lst = _lists.get(key, [])
        if end == -1:
            return lst[start:]
        return lst[start:end + 1]
    
    async def mock_lpush(key: str, *values: str):
        if key not in _lists:
            _lists[key] = []
        for v in reversed(values):
            _lists[key].insert(0, v)
        return len(_lists[key])
    
    async def mock_rpush(key: str, *values: str):
        if key not in _lists:
            _lists[key] = []
        _lists[key].extend(values)
        return len(_lists[key])
    
    async def mock_ltrim(key: str, start: int, end: int):
        if key in _lists:
            if end == -1:
                _lists[key] = _lists[key][start:]
            else:
                _lists[key] = _lists[key][start:end + 1]
        return True
    
    async def mock_llen(key: str):
        return len(_lists.get(key, []))
    
    # Set operations
    async def mock_sadd(key: str, *values: str):
        if key not in _sets:
            _sets[key] = set()
        count = 0
        for v in values:
            if v not in _sets[key]:
                _sets[key].add(v)
                count += 1
        return count
    
    async def mock_srem(key: str, *values: str):
        if key not in _sets:
            return 0
        count = 0
        for v in values:
            if v in _sets[key]:
                _sets[key].remove(v)
                count += 1
        return count
    
    async def mock_sismember(key: str, value: str):
        return value in _sets.get(key, set())
    
    async def mock_smembers(key: str):
        return _sets.get(key, set()).copy()
    
    # Hash operations
    async def mock_hget(key: str, field: str):
        return _hashes.get(key, {}).get(field)
    
    async def mock_hset(key: str, field: str = None, value: str = None, mapping: dict = None):
        if key not in _hashes:
            _hashes[key] = {}
        if mapping:
            _hashes[key].update(mapping)
        elif field is not None:
            _hashes[key][field] = value
        return 1
    
    async def mock_hgetall(key: str):
        return _hashes.get(key, {}).copy()
    
    async def mock_hdel(key: str, *fields: str):
        if key not in _hashes:
            return 0
        count = 0
        for f in fields:
            if f in _hashes[key]:
                del _hashes[key][f]
                count += 1
        return count
    
    async def mock_hincrby(key: str, field: str, amount: int):
        if key not in _hashes:
            _hashes[key] = {}
        current = int(_hashes[key].get(field, "0"))
        _hashes[key][field] = str(current + amount)
        return current + amount
    
    async def mock_ping():
        return True
    
    async def mock_flushdb():
        _storage.clear()
        _sets.clear()
        _lists.clear()
        _hashes.clear()
        return True
    
    # Scan iterator
    async def mock_scan_iter(match: str = "*", count: int = 100):
        import fnmatch
        for key in list(_storage.keys()) + list(_sets.keys()) + list(_lists.keys()):
            if fnmatch.fnmatch(key, match):
                yield key
    
    # Pipeline mock
    class MockPipeline:
        def __init__(self):
            self._operations = []
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            pass
        
        async def delete(self, key):
            self._operations.append(("delete", key))
        
        async def rpush(self, key, *values):
            self._operations.append(("rpush", key, values))
        
        async def lpush(self, key, *values):
            self._operations.append(("lpush", key, values))
        
        async def ltrim(self, key, start, end):
            self._operations.append(("ltrim", key, start, end))
        
        async def expire(self, key, ttl):
            self._operations.append(("expire", key, ttl))
        
        async def execute(self):
            results = []
            for op in self._operations:
                if op[0] == "delete":
                    results.append(await mock_delete(op[1]))
                elif op[0] == "rpush":
                    results.append(await mock_rpush(op[1], *op[2]))
                elif op[0] == "lpush":
                    results.append(await mock_lpush(op[1], *op[2]))
                elif op[0] == "ltrim":
                    results.append(await mock_ltrim(op[1], op[2], op[3]))
                elif op[0] == "expire":
                    results.append(await mock_expire(op[1], op[2]))
            self._operations = []
            return results
    
    def pipeline():
        return MockPipeline()
    
    # Assign all mocks
    redis.get = mock_get
    redis.set = mock_set
    redis.setex = mock_setex
    redis.delete = mock_delete
    redis.exists = mock_exists
    redis.expire = mock_expire
    redis.incr = mock_incr
    redis.incrby = mock_incrby
    redis.decr = mock_decr
    redis.decrby = mock_decrby
    redis.lrange = mock_lrange
    redis.lpush = mock_lpush
    redis.rpush = mock_rpush
    redis.ltrim = mock_ltrim
    redis.llen = mock_llen
    redis.sadd = mock_sadd
    redis.srem = mock_srem
    redis.sismember = mock_sismember
    redis.smembers = mock_smembers
    redis.hget = mock_hget
    redis.hset = mock_hset
    redis.hgetall = mock_hgetall
    redis.hdel = mock_hdel
    redis.hincrby = mock_hincrby
    redis.ping = mock_ping
    redis.flushdb = mock_flushdb
    redis.scan_iter = mock_scan_iter
    redis.pipeline = pipeline
    redis.publish = AsyncMock(return_value=1)
    
    # Expose storage for assertions
    redis._storage = _storage
    redis._sets = _sets
    redis._lists = _lists
    redis._hashes = _hashes
    
    return redis


@pytest.fixture
def cache_service(mock_redis_full) -> CacheService:
    """Create CacheService with mock Redis."""
    return CacheService(mock_redis_full)


@pytest.fixture
def cache_invalidator(cache_service) -> CacheInvalidator:
    """Create CacheInvalidator with mock CacheService."""
    return CacheInvalidator(cache_service)
