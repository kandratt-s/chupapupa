"""
Конфигурация для API Gateway CHUPAPUPA v2.0
Отвечает за настройки сервисов, безопасности и общих параметров.
"""

import os
from typing import List

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Настройки API Gateway.
    Загружаются из переменных окружения или .env файла.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # === ОСНОВНЫЕ НАСТРОЙКИ ===
    SERVICE_NAME: str = "api-gateway"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # === НАСТРОЙКИ СЕРВЕРА ===
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # === URL МИКРОСЕРВИСОВ ===
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    EVENT_SERVICE_URL: str = "http://event-service:8004"
    ATTENDANCE_SERVICE_URL: str = "http://attendance-service:8003"
    USER_STATISTIC_SERVICE_URL: str = "http://user-statistic-service:8006"
    ADMIN_SERVICE_URL: str = "http://admin-service:8000"
    BOT_SERVICE_URL: str = "http://bot-service:8000"
    WEB_SERVICE_URL: str = "http://web-service:8000"

    # === БЕЗОПАСНОСТЬ ===
    JWT_SECRET_KEY: str = "chupapupa-shared-super-secret-key-2025"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    # === CORS ===
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"

    # === ТАЙМАУТЫ И ЛИМИТЫ ===
    REQUEST_TIMEOUT: float = 30.0
    AUTH_TIMEOUT: float = 5.0
    HEALTH_CHECK_TIMEOUT: float = 5.0

    # === ПУБЛИЧНЫЕ ЭНДПОИНТЫ ===
    PUBLIC_ENDPOINTS: List[str] = [
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/",
        "/routes",
        "/stats",
        "/auth/login",
        "/auth/login-email",
        "/auth/register",
        "/auth/refresh",
        "/auth/verify-token",
        "/api/auth/login",
        "/api/auth/login-email",
        "/api/auth/register",
        "/api/auth/refresh",
        "/api/auth/verify-token",
    ]

    @computed_field
    @property
    def cors_origins_list(self) -> List[str]:
        """Преобразование строки CORS_ORIGINS в список."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @computed_field
    @property
    def cors_methods_list(self) -> List[str]:
        """Преобразование строки CORS_ALLOW_METHODS в список."""
        return [method.strip() for method in self.CORS_ALLOW_METHODS.split(",") if method.strip()]

    @computed_field
    @property
    def cors_headers_list(self) -> List[str]:
        """Преобразование строки CORS_ALLOW_HEADERS в список."""
        return [header.strip() for header in self.CORS_ALLOW_HEADERS.split(",") if header.strip()]

    @computed_field
    @property
    def SERVICE_ROUTES(self) -> dict[str, str]:
        """Маппинг маршрутов на микросервисы"""
        return {
            "/auth": self.AUTH_SERVICE_URL,
            "/api/auth": self.AUTH_SERVICE_URL,
            "/events": self.EVENT_SERVICE_URL,
            "/api/events": self.EVENT_SERVICE_URL,
            "/attendances/admin": self.ATTENDANCE_SERVICE_URL,
            "/attendances": self.ATTENDANCE_SERVICE_URL,
            "/api/attendances": self.ATTENDANCE_SERVICE_URL,
            "/user-statistics": self.USER_STATISTIC_SERVICE_URL,
            "/api/user-statistics": self.USER_STATISTIC_SERVICE_URL,
            "/admin": self.ADMIN_SERVICE_URL,
            "/api/admin": self.ADMIN_SERVICE_URL,
            "/bot": self.BOT_SERVICE_URL,
            "/api/bot": self.BOT_SERVICE_URL,
            "/web": self.WEB_SERVICE_URL,
            "/api/web": self.WEB_SERVICE_URL,
        }


# Глобальный экземпляр настроек
settings = Settings()
