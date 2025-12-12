"""Attendance service models."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from shared.base_model import BaseModel


class Attendance(BaseModel):
    """Attendance record model."""

    __tablename__ = "attendance_records"
    __table_args__ = {"schema": "attendance_service"}

    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    event_id: Mapped[int] = mapped_column(nullable=False, index=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_approved: Mapped[bool] = mapped_column(nullable=False, default=False)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Attendance id={self.id} user_id={self.user_id} event_id={self.event_id}>"
