"""
Модели данных для работы с базой данных.
Определяет структуру таблицы пользователей в БД в соответствии с реальной схемой проекта.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для декларативных моделей (SQLAlchemy 2.0)."""

    pass


class User(Base):
    """
    Модель пользователя в системе userStatistic_service.
    Соответствует реальной структуре таблицы в проекте с английскими названиями полей.
    """

    __tablename__ = "users"

    # Главный ключ таблицы (автоинкремент, уникальный)
    user_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
        comment="Главный ключ таблицы",
    )

    # Персональные данные студента
    last_name = Column(String(100), nullable=False, comment="Фамилия студента")
    first_name = Column(String(100), nullable=False, comment="Имя студента")
    middle_name = Column(
        String(100), nullable=True, comment="Отчество студента (может быть пусто)"
    )

    # Учебная информация
    group_name = Column(
        String(20), nullable=False, comment="Учебная группа (например: 24КНТ-7, 23БИ-1)"
    )

    # Контактная информация
    hs_email = Column(
        String(100), unique=True, nullable=False, comment="Электронная почта студента"
    )
    tg_id = Column(
        String(50), unique=True, nullable=True, comment="ID телеграма (не никнейм)"
    )
    tg_name = Column(
        String(100), nullable=True, comment="Ник в телеграме через @, например @Kan"
    )

    # Система баллов
    practice_points = Column(
        Float, default=0.0, nullable=False, comment="Число набранных очков за практику"
    )

    # Файловая система
    photo_path = Column(
        String(500), nullable=True, comment="Локальный путь до файла фото в проекте"
    )

    # Метаданные (добавляем для удобства работы)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Дата создания записи",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Дата последнего обновления",
    )

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, name='{self.first_name} {self.last_name}', group='{self.group_name}', tg_name='{self.tg_name}')>"
