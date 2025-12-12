"""Event service models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.base_model import BaseModel


class Event(BaseModel):
    """Event model."""

    __tablename__ = "events"
    __table_args__ = {"schema": "event_service"}

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_profile: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Event id={self.id} name={self.name}>"
