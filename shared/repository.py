"""Base repository for CRUD operations."""

from typing import Any, Generic, TypeVar, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.base_model import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Base repository for CRUD operations."""

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        """Initialize repository.

        Args:
            session: Database session.
            model: SQLAlchemy model class.
        """
        self.session = session
        self.model = model

    async def create(self, **kwargs: Any) -> T:
        """Create a new record.

        Args:
            **kwargs: Model fields to set.

        Returns:
            T: Created model instance.
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get_by_id(self, id: int) -> T | None:
        """Get record by ID.

        Args:
            id: Record ID.

        Returns:
            Optional[T]: Model instance or None if not found.
        """
        return await self.session.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """Get all records with pagination.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List[T]: List of model instances.
        """
        query = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return cast(list[T], result.scalars().all())

    async def update(self, id: int, **kwargs: Any) -> T | None:
        """Update a record.

        Args:
            id: Record ID.
            **kwargs: Fields to update.

        Returns:
            Optional[T]: Updated model instance or None if not found.
        """
        instance = await self.get_by_id(id)
        if not instance:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        return instance

    async def delete(self, id: int) -> bool:
        """Delete a record.

        Args:
            id: Record ID.

        Returns:
            bool: True if deleted, False if not found.
        """
        instance = await self.get_by_id(id)
        if not instance:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def count(self) -> int:
        """Count total records.

        Returns:
            int: Total number of records.
        """
        query = select(func.count()).select_from(self.model)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def commit(self) -> None:
        """Commit current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback current transaction."""
        await self.session.rollback()
