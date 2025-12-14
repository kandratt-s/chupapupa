"""
Конфигурация для микросервиса userStatistic.
Отвечает за настройки подключения к базе данных, логирование и другие параметры.
"""

from pydantic_settings import BaseSettings


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
    DATABASE_URL: str = "postgresql://user_statistic_user:user_statistic_pass@postgres:5432/chupapupa_pj"

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
