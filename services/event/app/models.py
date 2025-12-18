"""
Модели данных для работы с базой данных Event сервиса.
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Event(Base):
    """
    Модель события в системе event_service.
    Соответствует таблице event_service.events.
    """

    __tablename__ = "events"
    __table_args__ = {"schema": "event_service"}

    # Основные поля
    event_id = Column(
        Integer, primary_key=True, autoincrement=True, comment="Уникальный ID события"
    )
    name = Column(String(255), nullable=False, comment="Название события")
    date = Column(DateTime(timezone=True), nullable=False, comment="Дата и время события")
    profilnoe = Column(Boolean, nullable=False, default=False, comment="Профильное мероприятие")
    opisanie = Column(Text, nullable=True, comment="Описание события")
    active = Column(Boolean, nullable=False, default=True, comment="Активность события")

    # Технические поля
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Дата создания")
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Дата обновления",
    )

    def __repr__(self) -> str:
        """Строковое представление объекта."""
        return f"<Event(event_id={self.event_id}, name='{self.name}', active={self.active})>"
