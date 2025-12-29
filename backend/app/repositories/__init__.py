"""
Repository layer for data access.

Provides a clean abstraction over SQLAlchemy for database operations.
All database access should go through repositories, not direct session usage.

Repositories:
    - BaseRepository: Generic CRUD operations
    - UserRepository: User-specific operations (auth, social graph)
    - PostRepository: Post-specific operations (feeds, likes)
"""

from app.repositories.base import BaseRepository
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository", 
    "PostRepository",
]
