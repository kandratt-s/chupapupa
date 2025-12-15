"""
Эндпоинты для работы с пользователями.
Обрабатывает запросы от пользователей (получение информации о себе или других пользователях).
"""

import httpx
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.crud import user_crud
from app.core.dependencies import optional_user, user_required
from app.database import get_db
from app.schemas import UserResponse, UserCreate
from app.services.photo_service import PhotoService

router: APIRouter = APIRouter(prefix="/users", tags=["users"])

# Инициализация сервиса для работы с фотографиями
photo_service = PhotoService()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Самостоятельная регистрация нового пользователя с фото",
    description="""
    Регистрация нового пользователя в системе с обязательной загрузкой фото.

    Автоматически проверяет:
    - Уникальность HSE email и Telegram ID
    - Валидность входных данных
    - Правильность формата Telegram username
    - Корректность загруженного изображения

    При создании автоматически устанавливается:
    - Дата создания
    - Начальное количество баллов (0)
    - Статус активности (активен)
    - Сохранение фотографии в папку faces
    """,
)
async def register_user(
    first_name: str = Form(..., description="Имя"),
    last_name: str = Form(..., description="Фамилия"), 
    middle_name: Optional[str] = Form(None, description="Отчество"),
    group_name: str = Form(..., description="Группа"),
    hse_email: str = Form(..., description="HSE email"),
    tg_id: Optional[str] = Form(None, description="Telegram ID"),
    tg_name: Optional[str] = Form(None, description="Telegram username"),
    password: str = Form(..., min_length=6, description="Пароль (минимум 6 символов)"),
    photo: UploadFile = File(..., description="Фотография пользователя"),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Создать нового пользователя (самостоятельная регистрация) с фотографией и авторизацией.

    Создает записи в двух сервисах:
    1. UserStatistic - основная информация пользователя
    2. Auth - данные для авторизации (пароль)

    Args:
        first_name: Имя пользователя
        last_name: Фамилия пользователя
        middle_name: Отчество (опционально)
        group_name: Учебная группа
        hse_email: HSE email
        tg_id: Telegram ID (опционально)  
        tg_name: Telegram username (опционально)
        password: Пароль для входа в систему
        photo: Файл фотографии
        db: Сессия базы данных

    Returns:
        UserResponse: Созданный пользователь

    Raises:
        HTTPException 400: Если пользователь с такими данными уже существует или фото некорректное
        HTTPException 422: Если данные не прошли валидацию
        HTTPException 500: Если ошибка при создании auth записи
    """
    # Проверяем формат изображения
    if not photo.content_type or not photo.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Файл должен быть изображением"
        )
    
    try:
        # Создаем объект UserCreate из форм данных
        user_data = UserCreate(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            group_name=group_name,
            hse_email=hse_email,
            tg_id=tg_id,
            tg_name=tg_name
        )
        
        # Создаем пользователя в UserStatistic сервисе
        user = user_crud.create_user(db, user_data)
        
        # Сохраняем фото
        photo_path = await photo_service.save_user_photo(photo, user.user_id)
        
        # Обновляем путь к фото в базе
        if photo_path:
            user.photo_path = photo_path
            db.commit()
            db.refresh(user)
        
        # Создаем auth запись для пользователя
        try:
            async with httpx.AsyncClient() as client:
                auth_data = {
                    "user_id": user.user_id,
                    "password": password,
                    "role": "user"
                }
                auth_response = await client.post(
                    "http://auth-service:8001/create",
                    json=auth_data,
                    timeout=10.0
                )
                
                if auth_response.status_code != 200:
                    # Если не удалось создать auth запись, удаляем пользователя
                    db.delete(user)
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Ошибка создания учетной записи авторизации: {auth_response.text}"
                    )
                    
        except httpx.RequestError as e:
            # Если не удалось связаться с auth сервисом, удаляем пользователя
            db.delete(user)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка связи с сервисом авторизации: {str(e)}"
            )
            
        return create_user_response(user)
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


def create_user_response(user) -> UserResponse:
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
)
async def get_my_profile(
    current_user: dict[str, Any] = Depends(user_required), db: Session = Depends(get_db)
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

    return create_user_response(user)


@router.get(
    "/by-email",
    response_model=UserResponse,
    summary="Поиск пользователя по email",
    description="Поиск пользователя по HSE email адресу для аутентификации",
)
def get_user_by_email(
    email: str,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Получить пользователя по email адресу.
    
    Args:
        email: HSE email пользователя
        db: Сессия базы данных

    Returns:
        UserResponse: Информация о пользователе

    Raises:
        HTTPException 404: Пользователь не найден
    """
    user = user_crud.get_user_by_email(db, email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с email '{email}' не найден",
        )

    return UserResponse.model_validate(user)


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
)
async def get_user_profile(
    user_id: int,
    current_user: dict[str, Any] = Depends(optional_user),
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

    return create_user_response(user)


# =====================================================
# ЭНДПОИНТЫ ДЛЯ РАБОТЫ С ФОТОГРАФИЯМИ
# =====================================================

@router.post(
    "/me/photo",
    summary="Загрузить свою фотографию",
    description="""
    Загрузка фотографии текущего пользователя.
    
    Фотография сохраняется с именем {user_id}.{расширение} в папке faces/.
    Поддерживаемые форматы: JPG, PNG, GIF, BMP, WebP, TIFF.
    
    Если у пользователя уже есть фотография, она будет заменена.
    """,
)
async def upload_my_photo(
    photo: UploadFile = File(..., description="Фотография пользователя"),
    current_user: dict[str, Any] = Depends(user_required),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Загрузить фотографию текущего пользователя.

    Args:
        photo: Загружаемый файл фотографии
        current_user: Информация о текущем пользователе
        db: Сессия базы данных

    Returns:
        dict: Информация о сохраненной фотографии

    Raises:
        HTTPException 400: Неподдерживаемый формат файла
        HTTPException 404: Пользователь не найден  
        HTTPException 500: Ошибка сохранения файла
    """
    # Проверяем что пользователь существует
    user = user_crud.get_user_by_id(db, current_user["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    try:
        # Сохраняем фотографию
        file_path = await photo_service.update_user_photo(photo, current_user["user_id"])
        photo_url = photo_service.get_photo_url(current_user["user_id"])
        
        return {
            "message": "Фотография успешно загружена",
            "file_path": file_path,
            "photo_url": photo_url,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке фотографии: {str(e)}",
        )


@router.get(
    "/me/photo",
    summary="Получить свою фотографию",
    description="Получить фотографию текущего пользователя как файл",
)
async def get_my_photo(
    current_user: dict[str, Any] = Depends(user_required),
) -> FileResponse:
    """
    Получить фотографию текущего пользователя.

    Args:
        current_user: Информация о текущем пользователе

    Returns:
        FileResponse: Файл фотографии

    Raises:
        HTTPException 404: Фотография не найдена
    """
    photo_path = await photo_service.get_user_photo_path(current_user["user_id"])
    
    if not photo_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена",
        )

    return FileResponse(photo_path)


@router.delete(
    "/me/photo",
    summary="Удалить свою фотографию",
    description="Удалить фотографию текущего пользователя",
)
async def delete_my_photo(
    current_user: dict[str, Any] = Depends(user_required),
) -> dict[str, str]:
    """
    Удалить фотографию текущего пользователя.

    Args:
        current_user: Информация о текущем пользователе

    Returns:
        dict: Результат операции удаления

    Raises:
        HTTPException 404: Фотография не найдена
    """
    success = await photo_service.delete_user_photo(current_user["user_id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фотография не найдена или уже удалена",
        )

    return {"message": "Фотография успешно удалена"}


@router.get(
    "/{user_id}/photo",
    summary="Получить фотографию пользователя",
    description="Получить фотографию любого пользователя (доступно всем)",
)
async def get_user_photo(
    user_id: int,
    current_user: Optional[dict[str, Any]] = Depends(optional_user),
) -> FileResponse:
    """
    Получить фотографию пользователя по ID.

    Args:
        user_id: ID пользователя
        current_user: Информация о текущем пользователе (опционально)

    Returns:
        FileResponse: Файл фотографии

    Raises:
        HTTPException 404: Фотография не найдена
    """
    photo_path = await photo_service.get_user_photo_path(user_id)
    
    if not photo_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
        detail="Фотография пользователя не найдена",
    )

    return FileResponse(photo_path)


