"""
Администраторские эндпоинты для управления пользователями.
Предоставляет полный CRUD функционал для работы с пользователями.

Эти эндпоинты вызываются через admin сервис и предназначены только для администраторов.
"""

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.crud import user_crud
from app.core.dependencies import admin_required
from app.database import get_db
from app.schemas import (
    MessageResponse,
    UserCreate,
    UserListResponse,
    UserListWithPagination,
    UserResponse,
    UserUpdate,
)
from app.services.photo_service import PhotoService

router: APIRouter = APIRouter(prefix="/admin", tags=["admin"])

# Инициализация сервиса для работы с фотографиями
photo_service = PhotoService()


def create_user_response(user: Any) -> UserResponse:
    """
    Создать UserResponse с photo_url на основе объекта пользователя.

    Args:
        user: Объект пользователя из базы данных

    Returns:
        UserResponse: Пользователь с добавленным photo_url
    """
    user_data = UserResponse.from_orm(user)
    user_data.photo_url = photo_service.get_photo_url(user.user_id)
    return user_data


@router.get(
    "/users",
    response_model=UserListWithPagination,
    summary="Получить список всех пользователей",
    description="""
    Получение полного списка пользователей с пагинацией и поиском.

    Функционал:
    - Пагинация для работы с большими объемами данных
    - Поиск по имени, фамилии, отчеству или telegram username
    - Фильтрация по активности аккаунта
    - Сортировка по фамилии и имени

    Используется в админ-панели для:
    - Просмотра всех пользователей системы
    - Поиска конкретных пользователей
    - Управления пользователями
    """,
)
async def get_all_users(
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(50, ge=1, le=200, description="Количество записей на странице"),
    search: str | None = Query(None, description="Поиск по ФИО или Telegram"),
    active_only: bool = Query(False, description="Показать только активных пользователей"),
    current_user: dict[str, Any] = Depends(admin_required),
    db: Session = Depends(get_db),
) -> UserListWithPagination:
    """
    Получить пагинированный список пользователей.

    Args:
        page: Номер страницы (начинается с 1)
        per_page: Количество записей на странице (максимум 200)
        search: Строка поиска по ФИО или Telegram username
        active_only: Фильтр для показа только активных пользователей
        db: Сессия базы данных

    Returns:
        UserListWithPagination: Список пользователей с метаданными пагинации
    """
    skip = (page - 1) * per_page

    users, total = user_crud.get_users_list(
        db=db, skip=skip, limit=per_page, search=search, is_active_only=active_only
    )

    total_pages = (total + per_page - 1) // per_page

    return UserListWithPagination(
        users=[UserListResponse.from_orm(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Получить информацию о пользователе",
    description="""
    Получение полной информации о конкретном пользователе.

    Возвращает все данные пользователя, включая:
    - Персональную информацию
    - Telegram данные
    - Количество баллов
    - Статус администратора
    - Метаданные (даты создания/обновления)
    """,
)
async def get_user_by_id(
    user_id: int,
    current_user: dict[str, Any] = Depends(admin_required),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Получить информацию о пользователе по ID.

    Args:
        user_id: ID пользователя
        current_user: Информация о текущем пользователе
        db: Сессия базы данных

    Returns:
        UserResponse: Полная информация о пользователе

    Raises:
        HTTPException 404: Если пользователь не найден
    """
    user = user_crud.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {user_id} не найден",
        )

    return create_user_response(user)


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать нового пользователя",
    description="""
    Создание нового пользователя в системе.

    Автоматически проверяет:
    - Уникальность Telegram username и ID
    - Валидность входных данных
    - Правильность формата Telegram username

    При создании автоматически устанавливается:
    - Дата создания
    - Начальное количество баллов (0)
    - Статус активности (активен)
    """,
)
async def create_user(
    user_data: UserCreate,
    admin: dict[str, Any] = Depends(admin_required),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Создать нового пользователя.

    Args:
        user_data: Данные нового пользователя
        db: Сессия базы данных

    Returns:
        UserResponse: Созданный пользователь

    Raises:
        HTTPException 400: Если пользователь с такими данными уже существует
        HTTPException 422: Если данные не прошли валидацию
    """
    try:
        user = user_crud.create_user(db, user_data)
        return create_user_response(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Обновить информацию о пользователе",
    description="""
    Обновление информации о существующем пользователе.

    Позволяет обновлять любые поля пользователя:
    - Персональную информацию (ФИО)
    - Telegram данные
    - Количество баллов
    - Статус администратора
    - Статус активности

    Можно обновлять как отдельные поля, так и несколько сразу.
    Автоматически проверяет уникальность Telegram данных.
    """,
)
async def update_user_admin(
    user_id: int,
    user_update: UserUpdate,
    current_user: dict[str, Any] = Depends(admin_required),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Обновить информацию о пользователе.

    Args:
        user_id: ID пользователя для обновления
        user_update: Новые данные пользователя
        db: Сессия базы данных

    Returns:
        UserResponse: Обновленная информация о пользователе

    Raises:
        HTTPException 404: Если пользователь не найден
        HTTPException 400: Если новые данные конфликтуют с существующими
    """
    try:
        user = user_crud.update_user(db, user_id, user_update)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь с ID {user_id} не найден",
            )

        return create_user_response(user)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
    summary="Деактивировать пользователя",
    description="""
    Деактивация пользователя (мягкое удаление).

    Пользователь не удаляется из базы данных, а просто помечается как неактивный.
    Это позволяет сохранить историю и при необходимости восстановить аккаунт.

    После деактивации:
    - Пользователь не может войти в систему
    - Не отображается в списках активных пользователей
    - Сохраняются все данные и история
    """,
)
async def deactivate_user(
    user_id: int,
    current_user: dict[str, Any] = Depends(admin_required),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Деактивировать пользователя.

    Args:
        user_id: ID пользователя для деактивации
        db: Сессия базы данных

    Returns:
        MessageResponse: Сообщение о результате операции

    Raises:
        HTTPException 404: Если пользователь не найден
    """
    success = user_crud.delete_user(db, user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {user_id} не найден",
        )

    return MessageResponse(message=f"Пользователь с ID {user_id} успешно деактивирован")


@router.patch(
    "/users/{user_id}/points",
    response_model=UserResponse,
    summary="Изменить количество баллов пользователя",
    description="""
    Изменение баллов пользователя на указанную величину.

    Можно как добавлять баллы (положительное значение),
    так и отнимать (отрицательное значение).

    Баллы не могут стать отрицательными - минимальное значение 0.
    """,
)
async def update_user_points(
    user_id: int,
    points_delta: float = Query(..., description="Изменение баллов (может быть отрицательным)"),
    current_user: dict[str, Any] = Depends(admin_required),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Изменить баллы пользователя.

    Args:
        user_id: ID пользователя
        points_delta: Изменение баллов (положительное - добавить, отрицательное - отнять)
        db: Сессия базы данных

    Returns:
        UserResponse: Обновленная информация о пользователе

    Raises:
        HTTPException 404: Если пользователь не найден
    """
    user = user_crud.update_user_points(db, user_id, points_delta)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {user_id} не найден",
        )

    return create_user_response(user)


@router.patch(
    "/user/{user_id}/add-points",
    response_model=UserResponse,
    summary="Добавить баллы пользователю",
    description="""
    Добавление баллов пользователю. Используется системой для автоматического
    начисления баллов (например, при одобрении заявок на посещение мероприятий).

    Поддерживает как положительные, так и отрицательные значения.
    Баллы не могут стать отрицательными - минимальное значение 0.
    """,
)
async def add_user_points(
    user_id: int,
    points_data: dict[str, Any] = Body(...),  # {"points": float, "reason": str}
    current_user: dict[str, Any] = Depends(admin_required),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Добавить баллы пользователю.

    Args:
        user_id: ID пользователя
        points_data: {"points": изменение баллов, "reason": причина (опционально)}
        db: Сессия базы данных

    Returns:
        UserResponse: Обновленная информация о пользователе

    Raises:
        HTTPException 404: Если пользователь не найден
        HTTPException 400: Если некорректные данные
    """
    try:
        points_delta = points_data.get("points", 0)
        if not isinstance(points_delta, int | float):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Поле 'points' должно быть числом",
            )

        user = user_crud.add_user_points(db, user_id, points_delta)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь с ID {user_id} не найден",
            )

        return create_user_response(user)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка обновления баллов: {str(e)}",
        ) from e


@router.get(
    "/users/telegram/{telegram_username}",
    response_model=UserResponse,
    summary="Найти пользователя по Telegram username",
    description="""
    Поиск пользователя по Telegram username.

    Удобно для:
    - Быстрого поиска пользователя по известному username
    - Интеграции с Telegram ботом
    - Связывания аккаунтов
    """,
)
async def get_user_by_telegram(
    telegram_username: str,
    current_user: dict[str, Any] = Depends(admin_required),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Найти пользователя по Telegram username.

    Args:
        telegram_username: Telegram username (с @ или без)
        db: Сессия базы данных

    Returns:
        UserResponse: Информация о пользователе

    Raises:
        HTTPException 404: Если пользователь не найден
    """
    user = user_crud.get_user_by_tg_name(db, telegram_username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с Telegram username '{telegram_username}' не найден",
        )

    return create_user_response(user)
