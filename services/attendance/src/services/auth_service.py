"""
Сервис для работы с авторизацией и зависимостями
"""

from typing import Any

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session


async def get_current_user(
    x_user_id: int = Header(..., alias="X-User-ID"),
    x_user_role: str = Header(..., alias="X-User-Role"),
    x_telegram_id: int = Header(..., alias="X-Telegram-ID"),
) -> dict[str, Any]:
    """Получить текущего пользователя из заголовков"""
    return {"user_id": x_user_id, "role": x_user_role, "telegram_id": x_telegram_id}


async def require_admin(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Проверить права администратора"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return current_user


async def get_db() -> AsyncSession:
    """Получить сессию базы данных"""
    async for session in get_db_session():
        yield session
