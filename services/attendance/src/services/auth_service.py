"""
Сервис для работы с авторизацией и зависимостями
"""

from typing import Any

from fastapi import Depends, Header, HTTPException, status
from fastapi import Request
import jwt
SECRET_KEY = "chupapupa-shared-super-secret-key-2025"
ALGORITHM = "HS256"
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session



def decode_jwt_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный тип токена")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Истекший токен")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный токен")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ошибка разбора токена")

async def get_current_user(request: Request) -> dict[str, Any]:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется авторизация (нет Bearer токена)")
    token = auth_header.split(" ")[1]
    payload = decode_jwt_token(token)
    return {
        "user_id": payload.get("user_id"),
        "role": payload.get("role", "user"),
        "auth_type": "jwt"
    }


async def require_admin(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    """Проверить права администратора"""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return current_user


from collections.abc import AsyncGenerator

async def get_db() -> AsyncGenerator:
    """Получить сессию базы данных"""
    async for session in get_db_session():
        yield session
