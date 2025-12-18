"""
Сервис для работы с авторизацией и зависимостями
"""

import os
from collections.abc import AsyncGenerator
from typing import Any, cast

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "chupapupa-shared-super-secret-key-2025")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def decode_jwt_token(token: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = cast(
            dict[str, Any],
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]),
        )
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный тип токена"
            )
        return payload
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Истекший токен"
        ) from err
    except jwt.InvalidTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный токен"
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Ошибка разбора токена"
        ) from err


async def get_current_user(request: Request) -> dict[str, Any]:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется авторизация (нет Bearer токена)")
    token = auth_header.split(" ")[1]
    payload = decode_jwt_token(token)
    return {
        "user_id": payload.get("user_id"),
        "role": payload.get("role", "user"),
        "auth_type": "jwt",
    }


async def require_admin(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Проверить права администратора"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return current_user


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Получить сессию базы данных"""
    async for session in get_db_session():
        yield session
