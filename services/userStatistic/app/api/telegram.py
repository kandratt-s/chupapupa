"""
Специальные эндпоинты для работы с Telegram ботом.
Поддерживает авторизацию по telegram_user_id и все операции
как для обычных пользователей, так и для админов.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.crud import user_crud
from app.core.dependencies import admin_required, user_required
from app.database import get_db
from app.schemas import (
    TelegramAuthRequest,
    TelegramAuthResponse,
    UserResponse,
    UserUpdate,
)

router: APIRouter = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/auth", summary="Авторизация через Telegram")
async def telegram_auth(
    auth_data: TelegramAuthRequest, db: Session = Depends(get_db)
) -> TelegramAuthResponse:
    """
    Авторизация пользователя через Telegram ID.

    Если пользователь существует - возвращает его информацию.
    Если не существует - можно создать нового (опционально).

    Args:
        auth_data: Данные для авторизации
        db: Сессия базы данных

    Returns:
        TelegramAuthResponse: Информация о пользователе и его правах
    """
    user = user_crud.get_user_by_tg_id(db, auth_data.tg_id)

    if not user:
        # Можно попробовать найти по tg_name
        if auth_data.tg_name:
            user = user_crud.get_user_by_tg_name(db, auth_data.tg_name)
            if user:
                # Обновляем tg_id если нашли по tg_name
                user.tg_id = str(auth_data.tg_id)
                db.commit()
                db.refresh(user)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден. Необходима регистрация в Auth Service.",
        )

    # IMPORTANT: Роль должна определяться Auth Service, не здесь!
    # В продакшене этот эндпоинт должен обращаться к Auth Service
    # Для разработки оставляем стандартную роль

    return TelegramAuthResponse(
        user=UserResponse.from_orm(user),
        role="user",  # TODO: Получать из Auth Service
        authenticated=True,
    )


@router.get("/profile", summary="Получить профиль авторизованного пользователя")
async def get_telegram_profile(
    current_user: dict[str, Any] = Depends(user_required), db: Session = Depends(get_db)
) -> UserResponse:
    """
    Получить информацию о своем профиле для Telegram бота.

    Использует заголовок X-Telegram-ID для идентификации пользователя.
    """
    if current_user["source"] != "telegram":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот эндпоинт только для Telegram бота",
        )

    user = current_user.get("user_object")
    if not user:
        # Дополнительная проверка
        user = user_crud.get_user_by_id(db, current_user["user_id"])

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    return UserResponse.from_orm(user)


@router.get("/users", summary="[ADMIN] Список пользователей для Telegram админа")
async def telegram_admin_list_users(
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(
        10, ge=1, le=50, description="Количество на странице (макс. 50 для Telegram)"
    ),
    search: str | None = Query(None, description="Поиск по ФИО или Telegram"),
    current_user: dict[str, Any] = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Получить список пользователей для Telegram админа.

    Ограниченная версия для удобства отображения в Telegram.
    """
    if current_user["source"] != "telegram":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот эндпоинт только для Telegram бота",
        )

    skip = (page - 1) * per_page
    users, total = user_crud.get_users_list(db=db, skip=skip, limit=per_page, search=search)

    # Форматируем для удобного отображения в Telegram
    formatted_users = []
    for user in users:
        # IMPORTANT: Не определяем роль здесь - это должен делать Auth Service
        # В продакшене роль будет приходить через заголовки

        formatted_users.append(
            {
                "id": user.user_id,
                "name": f"{user.last_name} {user.first_name}",
                "group": user.group_name,
                "telegram": user.tg_name or "не указан",
                "points": user.practice_points,
                "is_admin": False,  # TODO: Получать из Auth Service
            }
        )

    return {
        "users": formatted_users,
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_next": skip + per_page < total,
    }


@router.get("/users/{user_id}", summary="[ADMIN] Информация о пользователе для Telegram")
async def telegram_admin_get_user(
    user_id: int,
    current_user: dict[str, Any] = Depends(admin_required),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Получить информацию о пользователе для Telegram админа.
    """
    if current_user["source"] != "telegram":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот эндпоинт только для Telegram бота",
        )

    user = user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    return UserResponse.from_orm(user)


@router.patch(
    "/users/{user_id}/points",
    summary="[ADMIN] Изменить баллы пользователя через Telegram",
)
async def telegram_admin_update_points(
    user_id: int,
    points_delta: float = Query(..., description="Изменение баллов"),
    current_user: dict[str, Any] = Depends(admin_required),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Изменить баллы пользователя через Telegram админ-бот.
    """
    if current_user["source"] != "telegram":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот эндпоинт только для Telegram бота",
        )

    user = user_crud.update_user_points(db, user_id, points_delta)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    return UserResponse.from_orm(user)


@router.put("/users/{user_id}", summary="[ADMIN] Обновить пользователя через Telegram")
async def telegram_admin_update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: dict[str, Any] = Depends(admin_required),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Обновить информацию о пользователе через Telegram админ-бот.
    """
    if current_user["source"] != "telegram":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот эндпоинт только для Telegram бота",
        )

    try:
        user = user_crud.update_user(db, user_id, user_update)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
            )
        return UserResponse.from_orm(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
