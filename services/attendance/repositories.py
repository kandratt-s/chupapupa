"""Attendance service repositories."""

from models import Attendance
from sqlalchemy import and_, select

from shared.repository import BaseRepository


class AttendanceRepository(BaseRepository[Attendance]):
    """Repository for Attendance model."""

    async def get_by_user_and_event(self, user_id: int, event_id: int) -> Attendance | None:
        """Get attendance record by user and event.

        Args:
            user_id: User ID.
            event_id: Event ID.

        Returns:
            Optional[Attendance]: Attendance record or None.
        """
        query = select(Attendance).where(
            and_(Attendance.user_id == user_id, Attendance.event_id == event_id)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_user_attendance(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[Attendance]:
        """Get attendance records for a user.

        Args:
            user_id: User ID.
            skip: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            list[Attendance]: List of attendance records.
        """
        query = select(Attendance).where(Attendance.user_id == user_id).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_event_attendance(
        self, event_id: int, skip: int = 0, limit: int = 100
    ) -> list[Attendance]:
        """Get attendance records for an event.

        Args:
            event_id: Event ID.
            skip: Number of records to skip.
            limit: Maximum number of records.

        Returns:
            list[Attendance]: List of attendance records.
        """
        query = select(Attendance).where(Attendance.event_id == event_id).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
