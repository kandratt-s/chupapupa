"""
Зависимости для Event сервиса.
Обработка авторизации через заголовки JWT из Gateway.
"""

from typing import Any

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


async def get_current_user(
    x_user_id: str | None = Header(None, alias="X-User-ID"),
    x_user_role: str | None = Header(None, alias="X-User-Role"),
    x_telegram_id: str | None = Header(None, alias="X-Telegram-ID"),
) -> dict[str, Any]:
    """
    Извлекает информацию о пользователе из заголовков.

    Event сервис получает авторизацию через Gateway,
    который передает роли и ID через заголовки.
    """
    # Проверяем наличие хотя бы одного идентификатора
    if not x_user_id and not x_telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация. Отсутствуют заголовки X-User-ID или X-Telegram-ID.",
        )

    # Определяем тип пользователя и ID
    if x_user_id:
        user_id = int(x_user_id)
        user_type = "web"
    elif x_telegram_id:
        user_id = int(x_telegram_id)
        user_type = "telegram"
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Некорректные заголовки авторизации."
        )

    # Определяем роль (по умолчанию user)
    role = x_user_role.lower() if x_user_role else "user"

    if role not in ["admin", "user"]:
        role = "user"

    return {
        "user_id": user_id,
        "user_type": user_type,
        "role": role,
        "telegram_id": int(x_telegram_id) if x_telegram_id else None,
        "is_admin": role == "admin",
    }


async def require_admin(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """
    Зависимость для проверки прав администратора.
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Требуются права администратора."
        )

    return current_user


async def get_db_session() -> AsyncSession:
    """
    Алиас для get_db для единообразия с другими зависимостями.
    """
    async for db in get_db():
        yield db
