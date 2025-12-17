"""User Statistic service repositories."""

from typing import Any, Generic, TypeVar

from app.models import UserStatistic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Простая замена BaseRepository без shared зависимости
T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository for CRUD operations."""

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self.session = session
        self.model = model

    async def create(self, **kwargs: Any) -> T:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get_by_id(self, id: int) -> T | None:
        """Get record by ID."""
        return await self.session.get(self.model, id)

    async def commit(self) -> None:
        """Commit transaction."""
        await self.session.commit()


class UserStatisticRepository(BaseRepository[UserStatistic]):
    """Repository for UserStatistic model."""

    async def get_by_user_id(self, user_id: int) -> UserStatistic | None:
        """Get statistics by user ID.

        Args:
            user_id: User ID.

        Returns:
            Optional[UserStatistic]: User statistics or None.
        """
        query = select(UserStatistic).where(UserStatistic.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_top_users(self, limit: int = 10) -> list[UserStatistic]:
        """Get top users by average rating.

        Args:
            limit: Maximum number of records.

        Returns:
            list[UserStatistic]: List of top users.
        """
        query = (
            select(UserStatistic)
            .order_by(UserStatistic.average_rating.desc().nullslast())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
