"""
Главный роутер API для объединения всех эндпоинтов.
Собирает все роутеры и применяет общие настройки.
"""

from fastapi import APIRouter

from app.api import users, admin, telegram

# Создание главного роутера API
api_router = APIRouter()

# Подключение роутеров для различных групп эндпоинтов
api_router.include_router(users.router, tags=["users"])

api_router.include_router(admin.router, tags=["admin"])

api_router.include_router(telegram.router, tags=["telegram"])
