"""
Главный файл Event микросервиса.
Система управления событиями для ВШЭ.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from app.api import admin
from app.api import main as main_api
from app.core.config import settings
from app.database import close_db, get_db, init_db
from app.schemas import HealthResponse
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Управление жизненным циклом приложения."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


# Создаем FastAPI приложение
app = FastAPI(
    title="Event Microservice",
    description="Микросервис управления событиями для системы ВШЭ",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ==================== ОСНОВНЫЕ ЭНДПОИНТЫ ====================


@app.get("/", response_model=dict[str, Any], tags=["health"])
async def root() -> dict[str, Any]:
    """Корневой эндпоинт с информацией о сервисе."""
    return {"service": settings.SERVICE_NAME, "status": "running", "version": settings.VERSION}


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """
    Проверка состояния сервиса.
    Включает проверку подключения к базе данных.
    """
    db_status = "disconnected"

    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection failed"
        ) from err

    return HealthResponse(
        service=settings.SERVICE_NAME,
        status="healthy",
        database=db_status,
        port=settings.PORT,
        version=settings.VERSION,
    )


# Подключение API роутеров  
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(main_api.router, prefix="/events", tags=["events"])

# Примечание: uvicorn.run не нужен, так как приложение запускается через Docker
# с командой: uvicorn main:app --host 0.0.0.0 --port 8004 --reload
