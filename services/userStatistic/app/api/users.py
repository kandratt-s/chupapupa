"""
Эндпоинты для работы с пользователями.
Обрабатывает запросы от пользователей (получение информации о себе или других пользователях).
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.crud import user_crud
from app.core.dependencies import user_required, optional_user
from app.schemas import UserResponse

router: APIRouter = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Получить информацию о своем аккаунте",
    description="""
    Получение информации о своем аккаунте на основе user_id из заголовков.

    Используется для:
    - Получения пользователем информации о своем аккаунте
    - Проверки текущего количества баллов
    - Отображения профиля в веб-интерфейсе или боте

    Этот эндпоинт предназначен для использования обычными пользователями.
    """,
)  # type: ignore[misc]
async def get_my_profile(
    current_user: Dict[str, Any] = Depends(user_required), db: Session = Depends(get_db)
) -> UserResponse:
    """
    Получить информацию о своем профиле.

    Args:
        current_user: Информация о текущем пользователе из заголовков
        db: Сессия базы данных

    Returns:
        UserResponse: Полная информация о пользователе

    Raises:
        HTTPException 404: Если пользователь не найден
    """
    user = user_crud.get_user_by_id(db, current_user["user_id"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {current_user['user_id']} не найден",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт деактивирован"
        )

    return UserResponse.from_orm(user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Получить информацию о пользователе по ID",
    description="""
    Получение информации о пользователе по его ID.

    Пользователи могут получать информацию только о себе.
    Админы могут получать информацию о любом пользователе.

    Используется для:
    - Отображения профиля пользователя
    - Получения актуальной информации о баллах
    """,
)  # type: ignore[misc]
async def get_user_profile(
    user_id: int,
    current_user: Dict[str, Any] = Depends(optional_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Получить информацию о пользователе по ID.

    Args:
        user_id: ID пользователя
        current_user: Информация о текущем пользователе (может быть None для публичных запросов)
        db: Сессия базы данных

    Returns:
        UserResponse: Информация о пользователе

    Raises:
        HTTPException 404: Если пользователь не найден
        HTTPException 403: Если нет прав для просмотра информации
    """
    user = user_crud.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {user_id} не найден",
        )

    # Проверяем права доступа: пользователь может видеть только свою информацию,
    # админ - любую
    if current_user:
        if current_user["role"] != "admin" and current_user["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для просмотра информации о пользователе",
            )

    return UserResponse.from_orm(user)
