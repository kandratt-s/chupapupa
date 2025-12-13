"""
Конфигурация базы данных для Event сервиса.
"""

import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Базовый класс для декларативных моделей (SQLAlchemy 2.0)."""

    pass


# Создаем асинхронный движок
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Создаем фабрику сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения сессии базы данных.
    Используется в FastAPI через Depends().
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Инициализация базы данных."""
    # Создаем таблицы (только для разработки)
    # В продакшене используйте миграции
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Закрытие соединений с базой данных."""
    await engine.dispose()


# Функция для тестирования подключения
async def check_db_connection() -> bool:
    """Проверка подключения к базе данных."""
    try:
        async with async_session_maker() as session:
            await session.execute("SELECT 1")
            return True
    except Exception:
        return False


# Для совместимости с синхронными вызовами
def get_db_sync() -> AsyncSession:
    """Синхронная версия get_db для использования в обработчиках."""
    return asyncio.run(async_session_maker().__aenter__())
