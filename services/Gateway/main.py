"""
Главный файл FastAPI приложения для API Gateway CHUPAPUPA v2.0

Отвечает за:
- Инициализацию FastAPI приложения
- Подключение роутеров
- Настройку CORS и middleware
- Конфигурацию логирования
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from app.api import main as main_api
from app.api import proxy as proxy_api
from app.core.config import settings
from app.core.middleware import logging_middleware
from app.services.proxy import proxy_service
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Управление жизненным циклом приложения"""
    # Startup
    logger.info(f"🚀 CHUPAPUPA API Gateway v2.0 starting in {settings.ENVIRONMENT} mode")
    logger.info(f"🌐 Listening on {settings.HOST}:{settings.PORT}")
    logger.info(f"🔗 Available services: {len(settings.SERVICE_ROUTES)}")

    for route, url in settings.SERVICE_ROUTES.items():
        logger.info(f"   {route} -> {url}")

    logger.info(f"🔒 Public endpoints: {len(settings.PUBLIC_ENDPOINTS)}")
    logger.info(f"🌍 CORS origins: {settings.CORS_ORIGINS}")

    yield

    # Shutdown
    await proxy_service.close()
    logger.info("🚫 CHUPAPUPA API Gateway v2.0 stopped")


# Создание FastAPI приложения
app = FastAPI(
    title="CHUPAPUPA API Gateway v2.0",
    description="Центральная точка доступа ко всем микросервисам системы CHUPAPUPA",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Логирование middleware
app.middleware("http")(logging_middleware)

# Подключение роутеров
app.include_router(main_api.router, tags=["Gateway"])

# Proxy router должен быть последним для перехвата всех остальных путей
app.include_router(proxy_api.router, tags=["Proxy"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )