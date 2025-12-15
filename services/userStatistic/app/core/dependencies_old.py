"""
Зависимости для получения информации о пользователе.
Поддерживает JWT авторизацию через заголовок Authorization.
"""

from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.crud import user_crud
from app.core.jwt_auth import get_current_user_from_jwt, get_optional_user_from_jwt
from app.database import get_db


def get_current_user() -> dict[str, Any] | None:
    """
    Получение информации о текущем пользователе из JWT токена.
    Теперь используется прямая JWT авторизация вместо заголовков от Gateway.
    
    Returns:
        Dict с user_id, role, auth_type или None если токен отсутствует
    """
    return Depends(get_optional_user_from_jwt)


def user_required(
    current_user_info: dict[str, Any] = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Зависимость, которая требует авторизованного пользователя с валидным JWT токеном.

    Raises:
        HTTPException 401: Если JWT токен отсутствует или невалидный

    Returns:
        Dict с информацией о пользователе
    """
    # Проверим что пользователь существует в базе
    user = user_crud.get_user_by_id(db, current_user_info["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {current_user_info['user_id']} не найден в системе",
        )
    
    # Добавляем объект пользователя для удобства
    current_user_info["user_object"] = user
    return current_user_info


def optional_user(
    current_user_info: dict[str, Any] | None = Depends(get_optional_user_from_jwt),
    db: Session = Depends(get_db),
) -> dict[str, Any] | None:
    """
    Зависимость для получения информации о пользователе (необязательно).
    
    Returns:
        Dict с информацией о пользователе или None если токен отсутствует
    """
    if not current_user_info:
        return None
        
    # Проверим что пользователь существует в базе
    user = user_crud.get_user_by_id(db, current_user_info["user_id"])
    if not user:
        return None
    
    current_user_info["user_object"] = user
    return current_user_info

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
