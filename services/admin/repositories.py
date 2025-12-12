"""Admin service repositories."""

from models import AdminUser, AuditLog
from sqlalchemy import select

from shared.repository import BaseRepository


class AdminUserRepository(BaseRepository[AdminUser]):
    """Repository for AdminUser model."""

    async def get_by_user_id(self, user_id: int) -> AdminUser | None:
        """Get admin user by user ID.

        Args:
            user_id: User ID.

        Returns:
            Optional[AdminUser]: Admin user record or None.
        """
        query = select(AdminUser).where(AdminUser.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_active_admins(self, skip: int = 0, limit: int = 100) -> list[AdminUser]:
        """Get all active admin users.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            list[AdminUser]: List of active admin users.
        """
        query = select(AdminUser).where(AdminUser.is_active.is_(True)).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog model."""

    async def get_logs_by_admin(
        self, admin_id: int, skip: int = 0, limit: int = 100
    ) -> list[AuditLog]:
        """Get audit logs by admin.

        Args:
            admin_id: Admin ID.
            skip: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            list[AuditLog]: List of audit logs.
        """
        query = (
            select(AuditLog)
            .where(AuditLog.admin_id == admin_id)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_logs_by_resource(
        self, resource_type: str, resource_id: int, skip: int = 0, limit: int = 100
    ) -> list[AuditLog]:
        """Get audit logs for a resource.

        Args:
            resource_type: Resource type.
            resource_id: Resource ID.
            skip: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            list[AuditLog]: List of audit logs.
        """
        query = (
            select(AuditLog)
            .where(
                (AuditLog.resource_type == resource_type) & (AuditLog.resource_id == resource_id)
            )
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
