"""
Главное приложение FastAPI для Attendance Service v2.0
"""

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.api import admin, users
from src.database import engine
from src.models.schemas import HealthResponse
from sqlalchemy import text

# Создание приложения
app = FastAPI(
    title="Attendance Service v2.0",
    description="Сервис управления посещаемостью мероприятий v2.0",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы для фотографий (общие тома)
app.mount("/static/attendances", StaticFiles(directory="/shared/photos/attendances"), name="attendances")
app.mount("/static/faces", StaticFiles(directory="/shared/photos/faces"), name="faces")

# Подключение маршрутов
app.include_router(users.router, prefix="/attendances", tags=["Users"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])


@app.on_event("startup")
async def startup_event() -> None:
    """Инициализация при запуске приложения"""
    print("🚀 Запуск Attendance Service v2.0")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Очистка при остановке приложения"""
    await engine.dispose()
    print("🚫 Attendance Service v2.0 остановлен")


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Проверка здоровья сервиса"""

    # Проверяем подключение к базе данных
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        database_status = "disconnected"

    return HealthResponse(
        service="attendance-service-v2",
        status="healthy" if database_status == "connected" else "unhealthy",
        database=database_status,
        port=8003,
        version="2.0.0",
    )


@app.get("/info")
async def root() -> dict[str, Any]:
    """Корневой endpoint"""
    return {
        "service": "attendance-service-v2",
        "version": "2.0.0",
        "description": "Сервис управления посещаемостью мероприятий v2.0",
        "docs": "/docs",
        "health": "/health",
    }


# Примечание: uvicorn.run не нужен, так как приложение запускается через Docker
# с командой: uvicorn main:app --host 0.0.0.0 --port 8003
