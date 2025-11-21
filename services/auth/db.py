from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os

class DatabaseSettings(BaseSettings):
    database_url: str = os.getenv( "AUTH_DATABASE_URL",
                "postgresql+asyncpg://auth_user:auth_pass@postgres:5432/chupapupa_pj")
    sync_database_url: str = os.getenv( "AUTH_SYNC_DATABASE_URL",
                "postgresql://auth_user:auth_pass@postgres:5432/chupapupa_pj")  # Для Alembic
    schema_name: str = os.getenv("AUTH_SCHEMA_NAME", "auth_service")

settings = DatabaseSettings()


engine = create_async_engine(settings.database_url, future=True, poolclass=NullPool,
                             connect_args={"server_settings": {"search_path": settings.schema_name}} )

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()