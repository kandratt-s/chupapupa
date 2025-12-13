"""User Statistic service repositories."""

from app.models import UserStatistic
from sqlalchemy import select

from shared.repository import BaseRepository


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
