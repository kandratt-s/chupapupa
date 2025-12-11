"""
Pydantic схемы для валидации входящих и исходящих данных.
Соответствуют реальной структуре таблицы userStatistic_service.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class UserBase(BaseModel):
    """
    Базовая схема пользователя с общими полями.
    Соответствует структуре таблицы userStatistic_service.
    """

    last_name: str = Field(
        ..., min_length=1, max_length=100, description="Фамилия студента"
    )
    first_name: str = Field(
        ..., min_length=1, max_length=100, description="Имя студента"
    )
    middle_name: Optional[str] = Field(
        None, max_length=100, description="Отчество студента (может быть пусто)"
    )
    group_name: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Учебная группа (например: 24КНТ-7, 23БИ-1)",
    )
    hs_email: str = Field(..., max_length=100, description="Электронная почта студента")
    tg_id: Optional[str] = Field(
        None, max_length=50, description="ID телеграма (не никнейм)"
    )
    tg_name: Optional[str] = Field(
        None, max_length=100, description="Ник в телеграме через @"
    )
    practice_points: float = Field(
        default=0.0, ge=0, description="Число набранных очков за практику"
    )
    photo_path: Optional[str] = Field(
        None, max_length=500, description="Локальный путь до файла фото"
    )

    @validator("tg_name")
    def validate_tg_name(cls, v: Optional[str]) -> Optional[str]:
        """Валидация tg_name - должен начинаться с @"""
        if v and not v.startswith("@"):
            v = "@" + v
        return v

    @validator("hs_email")
    def validate_email(cls, v: str) -> str:
        """Базовая валидация email"""
        if v and "@" not in v:
            raise ValueError("Некорректный email адрес")
        return v

    @validator("group_name")
    def validate_group(cls, v: str) -> str:
        """Валидация формата группы"""
        if v and len(v) < 3:
            raise ValueError("Некорректный формат группы")
        return v.upper()  # Приводим к верхнему регистру


class UserCreate(UserBase):
    """
    Схема для создания нового пользователя.
    Обязательны: фамилия, имя, группа, HSEmail
    """

    pass


class UserUpdate(BaseModel):
    """
    Схема для обновления существующего пользователя.
    Все поля опциональны - можно обновлять частично.
    """

    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    group_name: Optional[str] = Field(None, min_length=1, max_length=20)
    hs_email: Optional[str] = Field(None, max_length=100)
    tg_id: Optional[str] = Field(None, max_length=50)
    tg_name: Optional[str] = Field(None, max_length=100)
    practice_points: Optional[float] = Field(None, ge=0)
    photo_path: Optional[str] = Field(None, max_length=500)

    @validator("tg_name")
    def validate_tg_name(cls, v: Optional[str]) -> Optional[str]:
        """Валидация tg_name - должен начинаться с @"""
        if v and not v.startswith("@"):
            v = "@" + v
        return v

    @validator("hs_email")
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Базовая валидация email"""
        if v and "@" not in v:
            raise ValueError("Некорректный email адрес")
        return v

    @validator("group_name")
    def validate_group(cls, v: Optional[str]) -> Optional[str]:
        """Валидация формата группы"""
        if v and len(v) < 3:
            raise ValueError("Некорректный формат группы")
        return v.upper() if v else v


class UserResponse(UserBase):
    """
    Схема для возврата информации о пользователе.
    Включает user_id и метаданные.
    """

    user_id: int = Field(..., description="Главный ключ таблицы")
    created_at: datetime = Field(..., description="Дата создания записи")
    updated_at: datetime = Field(..., description="Дата последнего обновления")

    class Config:
        from_attributes = True  # Позволяет создавать из SQLAlchemy моделей


class UserListResponse(BaseModel):
    """
    Схема для возврата списка пользователей с краткой информацией.
    Используется в админских ручках для получения списка всех пользователей.
    """

    user_id: int
    last_name: str
    first_name: str
    middle_name: Optional[str]
    group_name: str
    tg_name: Optional[str]
    practice_points: float

    class Config:
        from_attributes = True


class UserListWithPagination(BaseModel):
    """
    Схема для возврата пагинированного списка пользователей.
    """

    users: list[UserListResponse]
    total: int = Field(..., description="Общее количество пользователей")
    page: int = Field(..., description="Текущая страница")
    per_page: int = Field(..., description="Количество записей на странице")
    total_pages: int = Field(..., description="Общее количество страниц")


class MessageResponse(BaseModel):
    """
    Стандартная схема для ответов с сообщением.
    Используется для подтверждения операций или ошибок.
    """

    message: str = Field(..., description="Сообщение о результате операции")


class ErrorResponse(BaseModel):
    """
    Схема для возврата ошибок.
    """

    error: str = Field(..., description="Описание ошибки")
    detail: Optional[str] = Field(None, description="Детали ошибки")


# Дополнительные схемы для удобства работы с Telegram
class TelegramAuthRequest(BaseModel):
    """
    Схема для авторизации через Telegram.
    """

    tg_id: str = Field(..., description="Telegram ID пользователя")
    tg_name: Optional[str] = Field(None, description="Telegram username")


class TelegramAuthResponse(BaseModel):
    """
    Ответ на авторизацию через Telegram.
    """

    user: UserResponse
    role: str = Field(..., description="Роль пользователя: student или admin")
    authenticated: bool = Field(True, description="Статус авторизации")
