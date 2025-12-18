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


def get_current_user(
    current_user_info: dict[str, Any] = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Требует валидный JWT и возвращает информацию о пользователе из БД.
    """
    user = user_crud.get_user_by_id(db, current_user_info["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {current_user_info['user_id']} не найден в системе",
        )
    current_user_info["user_object"] = user
    return current_user_info


def user_required(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Алиас для get_current_user для читаемости в роутерах.
    """
    return current_user


def optional_user(
    current_user_info: dict[str, Any] | None = Depends(get_optional_user_from_jwt),
    db: Session = Depends(get_db),
) -> dict[str, Any] | None:
    """
    Получает пользователя из JWT, если токен присутствует и пользователь существует.
    """
    if not current_user_info:
        return None
    user = user_crud.get_user_by_id(db, current_user_info["user_id"])
    if not user:
        return None
    current_user_info["user_object"] = user
    return current_user_info


def admin_required(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Зависимость, которая требует пользователя с правами администратора.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора.",
        )

    return current_user
