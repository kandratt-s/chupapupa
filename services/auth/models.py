"""
Модели данных для Auth сервиса.
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base


class Auth(Base):
    """
    Модель для таблицы аутентификации.
    Хранит данные для входа в систему.
    """
    __tablename__ = "auth"
    __table_args__ = {"schema": "auth_service"}

    user_id = Column(Integer, primary_key=True, comment="ID пользователя из userStatistic")
    password_hash = Column(String(255), nullable=False, comment="Хеш пароля")
    role = Column(String(20), nullable=False, default="user", comment="Роль пользователя")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Дата создания")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Дата обновления")

    def __repr__(self) -> str:
        return f"<Auth(user_id={self.user_id}, role='{self.role}')>"