"""Shared configuration for all services."""

from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    host: str = "postgres"
    port: int = 5432
    user: str
    password: str
    database: str = "chupapupa_pj"
    schema: str = "public"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

    @property
    def database_url(self) -> str:
        """Build database URL."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )

    class Config:
        env_file = ".env"
        env_prefix = "DB_"


class AppSettings(BaseSettings):
    """Application configuration settings."""

    service_name: str = "service"
    service_port: int = 8000
    service_host: str = "0.0.0.0"
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_prefix = "APP_"


class Settings(BaseSettings):
    """Combined application settings."""

    db: DatabaseSettings = DatabaseSettings()
    app: AppSettings = AppSettings()

    class Config:
        env_file = ".env"
        case_sensitive = False
