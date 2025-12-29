"""
Generic base repository with common CRUD operations.

Provides a foundation for all entity-specific repositories with:
- Type-safe generic operations
- Async SQLAlchemy 2.0 patterns
- Consistent error handling and logging
"""

import logging
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.db.base import Base

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic repository providing common CRUD operations.
    
    All entity repositories should inherit from this class and
    provide the model type parameter.
    
    Example:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: AsyncSession) -> None:
                super().__init__(db, User)
    """

    def __init__(self, db: AsyncSession, model: type[ModelType]) -> None:
        """
        Initialize repository.
        
        Args:
            db: Async SQLAlchemy session
            model: SQLAlchemy model class
        """
        self.db = db
        self.model = model
        self._model_name = model.__name__

    # =========================================================================
    # Read Operations
    # =========================================================================

    async def get(self, id: int) -> ModelType | None:
        """
        Get a single record by primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance if found, None otherwise
        """
        logger.debug(f"Fetching {self._model_name} with id={id}")
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: Any = None,
    ) -> Sequence[ModelType]:
        """
        Get multiple records with pagination.
        
        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            order_by: Column to order by (default: created_at desc)
            
        Returns:
            Sequence of model instances
        """
        logger.debug(f"Fetching {self._model_name} list: skip={skip}, limit={limit}")
        
        query = select(self.model)
        
        if order_by is not None:
            query = query.order_by(order_by)
        elif hasattr(self.model, "created_at"):
            query = query.order_by(self.model.created_at.desc())
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_ids(self, ids: list[int]) -> Sequence[ModelType]:
        """
        Get multiple records by their IDs.
        
        Args:
            ids: List of primary key values
            
        Returns:
            Sequence of found model instances
        """
        if not ids:
            return []
        
        logger.debug(f"Fetching {self._model_name} with ids={ids}")
        result = await self.db.execute(
            select(self.model).where(self.model.id.in_(ids))
        )
        return result.scalars().all()

    # =========================================================================
    # Count & Existence
    # =========================================================================

    async def count(self, **filters: Any) -> int:
        """
        Count records matching optional filters.
        
        Args:
            **filters: Column=value pairs to filter by
            
        Returns:
            Number of matching records
            
        Example:
            count = await repo.count(is_active=True, status="published")
        """
        query = select(func.count()).select_from(self.model)
        
        for column, value in filters.items():
            if hasattr(self.model, column):
                query = query.where(getattr(self.model, column) == value)
        
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def exists(self, **filters: Any) -> bool:
        """
        Check if any record exists matching the filters.
        
        Args:
            **filters: Column=value pairs to filter by
            
        Returns:
            True if at least one record exists
            
        Example:
            exists = await repo.exists(email="user@example.com")
        """
        return await self.count(**filters) > 0

    async def exists_by_id(self, id: int) -> bool:
        """
        Check if a record exists by ID.
        
        Args:
            id: Primary key value
            
        Returns:
            True if record exists
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.id == id)
        )
        return (result.scalar() or 0) > 0

    # =========================================================================
    # Create Operations
    # =========================================================================

    async def create(self, **kwargs: Any) -> ModelType:
        """
        Create a new record.
        
        Args:
            **kwargs: Column values for the new record
            
        Returns:
            Created model instance with generated ID
        """
        logger.debug(f"Creating {self._model_name}: {list(kwargs.keys())}")
        
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        
        logger.info(f"Created {self._model_name} with id={instance.id}")
        return instance

    async def create_many(self, items: list[dict[str, Any]]) -> Sequence[ModelType]:
        """
        Create multiple records in batch.
        
        Args:
            items: List of dictionaries with column values
            
        Returns:
            Sequence of created model instances
        """
        if not items:
            return []
        
        logger.debug(f"Creating {len(items)} {self._model_name} records")
        
        instances = [self.model(**item) for item in items]
        self.db.add_all(instances)
        await self.db.flush()
        
        for instance in instances:
            await self.db.refresh(instance)
        
        logger.info(f"Created {len(instances)} {self._model_name} records")
        return instances

    # =========================================================================
    # Update Operations
    # =========================================================================

    async def update(self, id: int, **kwargs: Any) -> ModelType | None:
        """
        Update a record by ID.
        
        Args:
            id: Primary key of record to update
            **kwargs: Column values to update
            
        Returns:
            Updated model instance, or None if not found
        """
        if not kwargs:
            return await self.get(id)
        
        logger.debug(f"Updating {self._model_name} id={id}: {list(kwargs.keys())}")
        
        await self.db.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
        )
        await self.db.flush()
        
        return await self.get(id)

    async def update_many(
        self,
        filters: dict[str, Any],
        values: dict[str, Any],
    ) -> int:
        """
        Update multiple records matching filters.
        
        Args:
            filters: Column=value pairs to filter records
            values: Column=value pairs to update
            
        Returns:
            Number of records updated
        """
        if not values:
            return 0
        
        query = update(self.model).values(**values)
        
        for column, value in filters.items():
            if hasattr(self.model, column):
                query = query.where(getattr(self.model, column) == value)
        
        result = await self.db.execute(query)
        await self.db.flush()
        
        logger.info(f"Updated {result.rowcount} {self._model_name} records")
        return result.rowcount

    # =========================================================================
    # Delete Operations
    # =========================================================================

    async def delete(self, id: int) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id: Primary key of record to delete
            
        Returns:
            True if record was deleted, False if not found
        """
        logger.debug(f"Deleting {self._model_name} id={id}")
        
        result = await self.db.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.db.flush()
        
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted {self._model_name} id={id}")
        
        return deleted

    async def delete_many(self, **filters: Any) -> int:
        """
        Delete multiple records matching filters.
        
        Args:
            **filters: Column=value pairs to filter records
            
        Returns:
            Number of records deleted
        """
        query = delete(self.model)
        
        for column, value in filters.items():
            if hasattr(self.model, column):
                query = query.where(getattr(self.model, column) == value)
        
        result = await self.db.execute(query)
        await self.db.flush()
        
        logger.info(f"Deleted {result.rowcount} {self._model_name} records")
        return result.rowcount

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _apply_filters(self, query: Select, **filters: Any) -> Select:
        """Apply equality filters to a query."""
        for column, value in filters.items():
            if hasattr(self.model, column):
                query = query.where(getattr(self.model, column) == value)
        return query

    # Aliases for backwards compatibility
    get_by_id = get
    get_all = get_multi
