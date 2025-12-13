"""
Конфигурация Event сервиса.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения."""

    # Информация о сервисе
    SERVICE_NAME: str = "event-service"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # Сетевые настройки
    HOST: str = "0.0.0.0"
    PORT: int = 8003

    # База данных
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "chupapupa"
    DB_PASSWORD: str = "chupapupaZXC"
    DB_NAME: str = "chupapupa_pj"
    DATABASE_URL: str | None = None

    # URL-ы других сервисов
    ADMIN_SERVICE_URL: str = "http://admin-service:8000"
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    GATEWAY_SERVICE_URL: str = "http://gateway-service:8080"

    # Настройки безопасности
    SECRET_KEY: str = "dev_secret_key_change_in_production"

    @property
    def database_url(self) -> str:
        """Получаем DATABASE_URL из переменной или собираем из отдельных параметров."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Глобальный экземпляр настроек
settings = Settings()
