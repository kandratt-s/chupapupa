"""User Statistic service models."""

from sqlalchemy import Float
from sqlalchemy.orm import Mapped, mapped_column

from shared.base_model import BaseModel


class UserStatistic(BaseModel):
    """User statistics model."""

    __tablename__ = "user_statistics"
    __table_args__ = {"schema": "user_statistic_service"}

    user_id: Mapped[int] = mapped_column(nullable=False, unique=True, index=True)
    events_attended: Mapped[int] = mapped_column(default=0)
    events_organized: Mapped[int] = mapped_column(default=0)
    total_hours: Mapped[float] = mapped_column(Float, default=0.0)
    average_rating: Mapped[float | None] = mapped_column(Float)
    last_activity: Mapped[str | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<UserStatistic id={self.id} user_id={self.user_id}>"
