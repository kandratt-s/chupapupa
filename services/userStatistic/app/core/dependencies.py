"""
Зависимости для получения информации о пользователе из заголовков.
Поддерживает авторизацию как через веб-интерфейс (JWT), так и через Telegram бот.
"""

from typing import Any

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.crud import user_crud
from app.database import get_db


async def get_current_user(
    x_user_id: str | None = Header(None, alias="X-User-ID"),
    x_user_role: str | None = Header(None, alias="X-User-Role"),
    x_telegram_id: str | None = Header(None, alias="X-Telegram-ID"),
    x_source: str | None = Header(None, alias="X-Source"),  # "web" или "telegram"
) -> dict[str, Any] | None:
    """
    Получение информации о текущем пользователе из заголовков.

    Поддерживает два способа авторизации:
    1. Через веб (X-User-ID + X-User-Role) - устанавливается Gateway после проверки JWT
    2. Через Telegram (X-Telegram-ID) - устанавливается при запросе от бота

    Returns:
        Dict с user_id, role, source и другой информацией или None
    """
    if x_user_id and x_user_role:
        # Веб-авторизация через JWT
        return {
            "user_id": int(x_user_id),
            "role": x_user_role,
            "source": x_source or "web",
            "telegram_id": None,
        }
    elif x_telegram_id:
        # Telegram-авторизация
        return {
            "telegram_id": x_telegram_id,
            "source": "telegram",
            "user_id": None,  # Будет определен позже из БД
            "role": None,  # Будет определен позже из БД
        }

    return None


async def resolve_user_from_headers(
    current_user_info: dict[str, Any] | None, db: Session
) -> dict[str, Any] | None:
    """
    Дополнительная логика для определения user_id из Telegram ID, если нужно.

    Args:
        current_user_info: Информация из заголовков
        db: Сессия базы данных

    Returns:
        Дополненная информация о пользователе
    """
    if not current_user_info:
        return None

    # Если это Telegram авторизация, попытаемся найти user_id
    if current_user_info.get("source") == "telegram" and current_user_info.get("telegram_id"):
        tg_id = current_user_info["telegram_id"]
        user = user_crud.get_user_by_tg_id(db, tg_id)
        if user:
            current_user_info.update(
                {
                    "user_id": user.user_id,
                    "role": "user",  # По умолчанию обычный пользователь
                    "user_object": user,
                }
            )

    return current_user_info


async def user_required(
    current_user_info: dict[str, Any] | None = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Зависимость, которая требует авторизованного пользователя.

    Raises:
        HTTPException 401: Если пользователь не авторизован

    Returns:
        Dict с информацией о пользователе
    """
    if not current_user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация. Отсутствуют заголовки X-User-ID или X-Telegram-ID.",
        )

    # Дополняем информацию если нужно
    resolved_user = await resolve_user_from_headers(current_user_info, db)
    if not resolved_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось определить пользователя.",
        )

    return resolved_user


async def optional_user(
    current_user_info: dict[str, Any] | None = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any] | None:
    """
    Зависимость для опциональной авторизации.
    Возвращает информацию о пользователе если он авторизован, иначе None.

    Returns:
        Dict с информацией о пользователе или None
    """
    if not current_user_info:
        return None

    # Дополняем информацию если нужно
    return await resolve_user_from_headers(current_user_info, db)


async def admin_required(
    current_user: dict[str, Any] = Depends(user_required),
) -> dict[str, Any]:
    """
    Зависимость, которая требует пользователя с правами администратора.

    Args:
        current_user: Информация о текущем пользователе

    Raises:
        HTTPException 403: Если у пользователя нет прав администратора

    Returns:
        Dict с информацией о пользователе
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора.",
        )

    return current_user


async def telegram_user_required(
    current_user_info: dict[str, Any] | None = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Зависимость специально для Telegram бота.
    Требует авторизации через X-Telegram-ID.

    Raises:
        HTTPException 401: Если авторизация не через Telegram

    Returns:
        Dict с информацией о пользователе
    """
    if not current_user_info or current_user_info.get("source") != "telegram":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация через Telegram (X-Telegram-ID).",
        )

    # Пытаемся найти пользователя по tg_id
    resolved_user = await resolve_user_from_headers(current_user_info, db)
    if not resolved_user or not resolved_user.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден. Необходима регистрация.",
        )

    return resolved_user
