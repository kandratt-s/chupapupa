"""Event service repositories."""

from datetime import UTC, datetime

from models import Event
from sqlalchemy import select

from shared.repository import BaseRepository


class EventRepository(BaseRepository[Event]):
    """Repository for Event model."""

    async def get_active_events(self, skip: int = 0, limit: int = 100) -> list[Event]:
        """Get all active events."""
        query = select(Event).where(Event.is_active.is_(True)).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_upcoming_events(self, skip: int = 0, limit: int = 100) -> list[Event]:
        """Get upcoming events (date >= now)."""
        now = datetime.now(UTC)
        query = (
            select(Event)
            .where(Event.is_active.is_(True), Event.date >= now)
            .order_by(Event.date)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_past_events(self, skip: int = 0, limit: int = 100) -> list[Event]:
        """Get past events (date < now)."""
        now = datetime.now(UTC)
        query = (
            select(Event)
            .where(Event.is_active.is_(True), Event.date < now)
            .order_by(Event.date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_profile_events(self, skip: int = 0, limit: int = 100) -> list[Event]:
        """Get profile events."""
        query = (
            select(Event)
            .where(Event.is_active.is_(True), Event.is_profile.is_(True))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
