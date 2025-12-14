"""
Конфигурация базы данных
"""

import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Параметры подключения к базе данных
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://chupapupa:chupapupaZXC@localhost:5432/chupapupa_pj"
)

# Создаем асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=False)

# Создаем фабрику сессий
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncSession:
    """Получить сессию базы данных"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def test_db_connection() -> bool:
    """Тест подключения к базе данных"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False
