"""
Зависимости для получения информации о пользователе из заголовков.
Поддерживает авторизацию как через веб-интерфейс (JWT), так и через Telegram бот.
"""

from typing import Dict, Optional, Any
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.crud import user_crud


async def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_telegram_id: Optional[str] = Header(None, alias="X-Telegram-ID"),
    x_source: Optional[str] = Header(None, alias="X-Source"),  # "web" или "telegram"
) -> Optional[Dict[str, Any]]:
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
    current_user_info: Optional[Dict[str, Any]], db: Session
) -> Optional[Dict[str, Any]]:
    """
    Преобразует информацию из заголовков в полную информацию о пользователе.

    Для Telegram авторизации ищет пользователя в БД по tgID.
    Для веб-авторизации возвращает данные как есть.

    ВАЖНО: Роль всегда должна приходить от Auth Service через заголовки!
    """
    if not current_user_info:
        return None

    if current_user_info["source"] == "telegram":
        # Для Telegram ищем пользователя по tgID
        user = user_crud.get_user_by_tg_id(db, current_user_info["telegram_id"])
        if user:
            # ВАЖНО: НЕ определяем роль здесь!
            # В продакшене роль должна приходить от Auth Service
            # Для разработки используем роль из заголовков или дефолт
            role = current_user_info.get("role", "student")  # Fallback для разработки

            return {
                "user_id": user.user_id,
                "role": role,
                "source": "telegram",
                "telegram_id": current_user_info["telegram_id"],
                "user_object": user,
            }
        return None
    else:
        # Для веб возвращаем как есть
        return current_user_info


async def admin_required(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_telegram_id: Optional[str] = Header(None, alias="X-Telegram-ID"),
    x_source: Optional[str] = Header(None, alias="X-Source"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Dependency для проверки прав администратора.

    Поддерживает проверку как для веб-авторизации, так и для Telegram.

    Returns:
        Dict с полной информацией о пользователе

    Raises:
        HTTPException 401: Если пользователь не авторизован
        HTTPException 403: Если пользователь не админ
    """
    # Получаем базовую информацию из заголовков
    current_user_info = await get_current_user(
        x_user_id, x_user_role, x_telegram_id, x_source
    )

    if not current_user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    # Резолвим полную информацию о пользователе
    user_info = await resolve_user_from_headers(current_user_info, db)

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    # Проверяем права админа
    if user_info["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )

    return user_info


async def user_required(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_telegram_id: Optional[str] = Header(None, alias="X-Telegram-ID"),
    x_source: Optional[str] = Header(None, alias="X-Source"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Dependency для проверки авторизации пользователя.

    Поддерживает авторизацию как через веб, так и через Telegram.

    Returns:
        Dict[str, Any]: Полная информация о пользователе
    """
    # Получаем базовую информацию из заголовков
    current_user_info = await get_current_user(
        x_user_id, x_user_role, x_telegram_id, x_source
    )

    if not current_user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    # Резолвим полную информацию о пользователе
    user_info = await resolve_user_from_headers(current_user_info, db)

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user_info


async def optional_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_telegram_id: Optional[str] = Header(None, alias="X-Telegram-ID"),
    x_source: Optional[str] = Header(None, alias="X-Source"),
    db: Session = Depends(get_db),
) -> Optional[Dict[str, Any]]:
    """
    Dependency для опциональной авторизации.

    Возвращает информацию о пользователе, если он авторизован, или None.
    Не выбрасывает ошибки авторизации.
    """
    try:
        current_user_info = await get_current_user(
            x_user_id, x_user_role, x_telegram_id, x_source
        )
        if current_user_info:
            return await resolve_user_from_headers(current_user_info, db)
        return None
    except Exception:
        return None
