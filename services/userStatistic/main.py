"""
Главный файл FastAPI приложения для микросервиса userStatistic.

Отвечает за:
- Инициализацию FastAPI приложения
- Подключение роутеров
- Настройку CORS и middleware
- Инициализацию базы данных
- Конфигурацию логирования
"""

import logging
from typing import Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import init_db, get_db
from app.api.main import api_router


# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger: logging.Logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Управление жизненным циклом приложения.

    Заменяет устаревшие @app.on_event("startup") и @app.on_event("shutdown").

    Выполняется при запуске и остановке сервиса:
    - Инициализация базы данных
    - Создание таблиц при необходимости
    - Логирование событий запуска/остановки

    Args:
        app: Экземпляр FastAPI приложения

    Yields:
        None: Контроль выполнения для времени работы приложения
    """
    # Инициализация при запуске
    logger.info(f"Запуск микросервиса {settings.SERVICE_NAME}")

    try:
        # Инициализация базы данных
        init_db()
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        raise

    logger.info(
        f"Сервис {settings.SERVICE_NAME} успешно запущен на порту {settings.PORT}"
    )

    yield

    # Завершение работы
    logger.info(f"Остановка микросервиса {settings.SERVICE_NAME}")


# Создание FastAPI приложения
app: FastAPI = FastAPI(
    title="UserStatistic Microservice",
    description="""
    Микросервис для управления пользователями и их статистикой.

    Функционал:
    - 👥 Управление пользователями (создание, просмотр, редактирование)
    - 🏆 Система баллов и достижений
    - 👑 Административные функции
    - 🤖 Поддержка Telegram бота
    - 🌐 Интеграция с веб-интерфейсом

    Эндпоинты:
    - `/users/*` - пользовательские операции
    - `/admin/*` - административные операции
    - `/telegram/*` - специальные эндпоинты для Telegram бота

    Авторизация:
    - Веб: через JWT токены (заголовки X-User-ID, X-User-Role)
    - Telegram: через Telegram ID (заголовок X-Telegram-ID)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,  # Современный способ управления жизненным циклом
)

# Настройка CORS для взаимодействия с веб-интерфейсом и другими сервисами
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене ограничить конкретными доменами
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"], response_model=Dict[str, str])  # type: ignore[misc]
async def root() -> Dict[str, str]:
    """
    Проверка состояния сервиса.

    tags=["health"] группирует эндпоинты в документации Swagger.
    Используется для health checks и мониторинга.

    Returns:
        Dict[str, str]: Базовая информация о сервисе
    """
    return {"service": settings.SERVICE_NAME, "status": "running", "version": "1.0.0"}


@app.get("/health", tags=["health"], response_model=Dict[str, Any])  # type: ignore[misc]
async def health_check() -> Dict[str, Any]:
    """
    Расширенная проверка здоровья сервиса.

    Проверяет:
    - Статус приложения
    - Доступность базы данных
    - Основные настройки

    Returns:
        Dict[str, Any]: Детальная информация о состоянии сервиса
    """
    try:
        # Проверка подключения к БД
        db: Session = next(get_db())
        db.execute(text("SELECT 1"))
        db_status: str = "connected"

    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        db_status = f"error: {str(e)}"

    return {
        "service": settings.SERVICE_NAME,
        "status": "healthy",
        "database": db_status,
        "port": settings.PORT,
        "version": "1.0.0",
    }


# Подключение API роутеров
app.include_router(api_router)

# Примечание: uvicorn.run не нужен, так как приложение запускается через Docker
# с командой: uvicorn main:app --host 0.0.0.0 --port 8006 --reload
