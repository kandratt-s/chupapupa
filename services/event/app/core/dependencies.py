"""
Зависимости для Event сервиса.
Обработка авторизации через заголовки JWT из Gateway.
"""

import os
from collections.abc import AsyncGenerator
from typing import Any, cast

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

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
    user_data = {
        "user_id": payload.get("user_id"),
        "role": payload.get("role", "user"),
        "auth_type": "jwt",
    }
    user_data["is_admin"] = user_data["role"] == "admin"
    return user_data


async def require_admin(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """
    Зависимость для проверки прав администратора.
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Требуются права администратора."
        )

    return current_user


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Алиас для get_db для единообразия с другими зависимостями.
    """
    async for db in get_db():
        yield db
