"""
Модели данных для Attendance Service v2.0
"""

from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func


# Создание базового класса для моделей
class Base(DeclarativeBase):
    pass


# Константы статусов заявок
PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
REVIEWING = "reviewing"


class AttendanceRecord(Base):
    """Модель записи о посещаемости"""

    __tablename__ = "attendance_records"
    __table_args__ = {"schema": "attendance_service"}

    attendance_id = Column(Integer, primary_key=True)
    event_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    photo_path = Column(String(500), nullable=True)  # Путь к файлу (фото или PDF)
    is_aproved = Column(Boolean, nullable=False, default=False)
    status = Column(Enum("pending", "approved", "rejected", "reviewing", name="attendance_status", schema="attendance_service"), nullable=False, default=PENDING)
    reviewed_by = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    checked_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        """Преобразование в словарь"""
        return {
            "attendance_id": self.attendance_id,
            "event_id": self.event_id,
            "user_id": self.user_id,
            "file_path": self.photo_path,
            "is_aproved": self.is_aproved,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }
