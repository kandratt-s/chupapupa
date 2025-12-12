"""Auth service repositories."""

from models import Role, User
from sqlalchemy import select

from shared.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model."""

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username.

        Args:
            username: Username to search for.

        Returns:
            Optional[User]: User instance or None.
        """
        query = select(User).where(User.username == username)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email.

        Args:
            email: Email to search for.

        Returns:
            Optional[User]: User instance or None.
        """
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all active users.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            list[User]: List of active users.
        """
        query = select(User).where(User.is_active.is_(True)).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class RoleRepository(BaseRepository[Role]):
    """Repository for Role model."""

    async def get_by_name(self, name: str) -> Role | None:
        """Get role by name.

        Args:
            name: Role name to search for.

        Returns:
            Optional[Role]: Role instance or None.
        """
        query = select(Role).where(Role.name == name)
        result = await self.session.execute(query)
        return result.scalars().first()
