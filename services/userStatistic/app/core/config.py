"""
Конфигурация для микросервиса userStatistic.
Отвечает за настройки подключения к базе данных, логирование и другие параметры.
"""

from pydantic_settings import BaseSettings
from pydantic import computed_field


class Settings(BaseSettings):  # type: ignore[misc]
    """
    Настройки приложения userStatistic.
    Загружаются из переменных окружения или .env файла.
    """

    # Основные настройки сервиса
    SERVICE_NAME: str = "userstatistic-service"
    HOST: str = "0.0.0.0"
    PORT: int = 8006

    # Настройки базы данных
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_NAME: str = "chupapupa_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Собираем DATABASE_URL из отдельных параметров."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Настройки логирования
    LOG_LEVEL: str = "INFO"

    # URL для внутренних обращений к другим сервисам (если понадобится)
    ADMIN_SERVICE_URL: str = "http://admin-service:8000"
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    GATEWAY_SERVICE_URL: str = "http://gateway-service:8080"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Игнорировать дополнительные переменные окружения


settings = Settings()
