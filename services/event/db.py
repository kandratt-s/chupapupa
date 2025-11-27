import os
from collections.abc import AsyncGenerator
from pathlib import Path

from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


class DatabaseSettings(BaseSettings):
    model_config = {
        "env_file": Path(__file__).parent / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    database_url: str = os.getenv(
        "EVENT_DATABASE_URL",
        "postgresql+asyncpg://event_user:event_pass@postgres:5432/chupapupa_pj",
    )
    sync_database_url: str = os.getenv(
        "EVENT_SYNC_DATABASE_URL",
        "postgresql://event_user:event_pass@postgres:5432/chupapupa_pj",
    )  # Для Alembic
    schema_name: str = os.getenv("EVENT_SCHEMA_NAME", "event_service")


settings = DatabaseSettings()


engine = create_async_engine(
    settings.database_url,
    future=True,
    poolclass=NullPool,
    connect_args={"server_settings": {"search_path": settings.schema_name}},
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
