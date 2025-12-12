import os
from collections.abc import AsyncGenerator
from pathlib import Path

from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


class DatabaseSettings(BaseSettings):
    """Database configuration for User Statistic service."""

    model_config = {
        "env_file": Path(__file__).parent / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    database_url: str = os.getenv(
        "USER_STATISTIC_DATABASE_URL",
        "postgresql+asyncpg://user_statistic_user:user_statistic_pass@postgres:5432/chupapupa_pj",
    )
    sync_database_url: str = os.getenv(
        "USER_STATISTIC_SYNC_DATABASE_URL",
        "postgresql://user_statistic_user:user_statistic_pass@postgres:5432/chupapupa_pj",
    )
    schema_name: str = os.getenv("USER_STATISTIC_SCHEMA_NAME", "user_statistic_service")
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False


settings = DatabaseSettings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.echo,
    pool_size=settings.pool_size,
    max_overflow=settings.max_overflow,
    pool_pre_ping=True,
    connect_args={"server_settings": {"search_path": settings.schema_name}},
)

# Create session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


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
