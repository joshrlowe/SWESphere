"""SQLAlchemy model mixins for common functionality."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamps to models.

    The updated_at field is automatically updated on every modification.

    Usage:
        class MyModel(Base, TimestampMixin):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)
    """

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        """Timestamp when the record was created."""
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
            index=True,
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        """Timestamp when the record was last updated."""
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )

    def touch(self) -> None:
        """Manually update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)


class SoftDeleteMixin:
    """
    Mixin that adds soft delete functionality to models.

    Instead of permanently deleting records, they are marked as deleted
    with a timestamp. Use the is_deleted property to check status.

    Usage:
        class MyModel(Base, SoftDeleteMixin):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)

        # Soft delete
        instance.soft_delete()

        # Check if deleted
        if instance.is_deleted:
            ...

        # Restore
        instance.restore()
    """

    @declared_attr
    def deleted_at(cls) -> Mapped[datetime | None]:
        """Timestamp when the record was soft deleted. None if not deleted."""
        return mapped_column(
            DateTime(timezone=True),
            nullable=True,
            default=None,
            index=True,
        )

    @property
    def is_deleted(self) -> bool:
        """Check if the record has been soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark the record as deleted without removing from database."""
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None


class TableNameMixin:
    """
    Mixin that automatically generates table name from class name.

    Converts CamelCase to snake_case and pluralizes.
    Example: UserPost -> user_posts
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        import re

        # Convert CamelCase to snake_case
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        # Simple pluralization (add 's' or 'es')
        if name.endswith(("s", "x", "z", "ch", "sh")):
            return f"{name}es"
        return f"{name}s"


class ReprMixin:
    """
    Mixin that provides a useful __repr__ for models.

    Shows the class name and primary key(s).
    """

    def __repr__(self) -> str:
        """Generate a string representation of the model."""
        # Get primary key columns
        pk_cols = [col.name for col in self.__table__.primary_key.columns]
        pk_values = ", ".join(f"{col}={getattr(self, col, None)}" for col in pk_cols)
        return f"<{self.__class__.__name__}({pk_values})>"


class ToDictMixin:
    """
    Mixin that adds to_dict() method for serialization.
    """

    def to_dict(
        self,
        exclude: set[str] | None = None,
        include: set[str] | None = None,
    ) -> dict[str, Any]:
        """
        Convert model to dictionary.

        Args:
            exclude: Set of field names to exclude
            include: Set of field names to include (if provided, only these are included)

        Returns:
            Dictionary representation of the model
        """
        exclude = exclude or set()
        result = {}

        for column in self.__table__.columns:
            if column.name in exclude:
                continue
            if include and column.name not in include:
                continue

            value = getattr(self, column.name)

            # Handle datetime serialization
            if isinstance(value, datetime):
                value = value.isoformat()

            result[column.name] = value

        return result


class BaseModelMixin(TimestampMixin, ReprMixin, ToDictMixin):
    """
    Combined mixin with all common functionality.

    Includes:
    - created_at, updated_at timestamps
    - Useful __repr__
    - to_dict() serialization

    Usage:
        class MyModel(Base, BaseModelMixin):
            __tablename__ = "my_table"
            id: Mapped[int] = mapped_column(primary_key=True)
    """

    pass
