"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.config import DatabaseSettings


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, settings: DatabaseSettings):
        """Initialize database manager.

        Args:
            settings: Database configuration settings.
        """
        self.settings = settings
        self.engine: AsyncEngine | None = None
        self.async_session_maker: async_sessionmaker[AsyncSession] | None = None

    async def initialize(self) -> None:
        """Initialize database engine and session factory."""
        self.engine = create_async_engine(
            self.settings.database_url,
            echo=self.settings.echo,
            pool_size=self.settings.pool_size,
            max_overflow=self.settings.max_overflow,
            pool_pre_ping=True,
            echo_pool=False,
        )

        self.async_session_maker = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            autoflush=False,
        )

    async def dispose(self) -> None:
        """Dispose of the database engine."""
        if self.engine:
            await self.engine.dispose()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session.

        Yields:
            AsyncSession: Database session.
        """
        if self.async_session_maker is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self.async_session_maker() as session:
            yield session

    async def health_check(self) -> bool:
        """Check database health.

        Returns:
            bool: True if database is healthy, False otherwise.
        """
        try:
            async with self.async_session_maker() as session:
                await session.execute("SELECT 1")
            return True
        except Exception:
            return False


# Global database manager instance
db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager.

    Returns:
        DatabaseManager: The global database manager instance.

    Raises:
        RuntimeError: If database manager is not initialized.
    """
    if db_manager is None:
        raise RuntimeError("Database manager not initialized")
    return db_manager


async def init_db(settings: DatabaseSettings) -> DatabaseManager:
    """Initialize database manager.

    Args:
        settings: Database configuration settings.

    Returns:
        DatabaseManager: Initialized database manager.
    """
    global db_manager
    db_manager = DatabaseManager(settings)
    await db_manager.initialize()
    return db_manager


async def close_db() -> None:
    """Close database connection."""
    global db_manager
    if db_manager:
        await db_manager.dispose()
        db_manager = None
