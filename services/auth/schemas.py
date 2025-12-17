"""
Схемы данных для Auth сервиса.
"""

from enum import Enum

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


# ========== AUTH SCHEMAS ==========


class LoginRequest(BaseModel):
    """Запрос на авторизацию"""

    user_id: int = Field(..., description="ID пользователя из userStatistic")
    password: str = Field(..., min_length=1, description="Пароль")


class EmailLoginRequest(BaseModel):
    """Запрос на авторизацию по email"""

    email: str = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=1, description="Пароль")


class AuthCreate(BaseModel):
    """Создание записи аутентификации"""

    user_id: int = Field(..., description="ID пользователя из userStatistic")
    password: str = Field(..., min_length=6, description="Пароль (минимум 6 символов)")
    role: UserRole = Field(UserRole.USER, description="Роль пользователя")


class AuthUpdate(BaseModel):
    """Обновление записи аутентификации"""

    password: str | None = Field(None, min_length=6, description="Новый пароль")
    role: UserRole | None = Field(None, description="Новая роль")


class AuthResponse(BaseModel):
    """Ответ с информацией об аутентификации"""

    user_id: int
    role: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ========== TOKEN SCHEMAS ==========


class Token(BaseModel):
    """JWT токены"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Время жизни access токена в секундах")


class TokenPayload(BaseModel):
    """Содержимое JWT токена"""

    user_id: int
    role: str
    exp: int
    iat: int
    type: str  # "access" или "refresh"

    class Config:
        from_attributes = True


class RefreshTokenRequest(BaseModel):
    """Запрос обновления токена"""

    refresh_token: str = Field(..., description="Refresh токен")


class ChangePasswordRequest(BaseModel):
    """Запрос смены пароля пользователем"""

    current_password: str = Field(..., min_length=1, description="Текущий пароль")
    new_password: str = Field(..., min_length=6, description="Новый пароль (минимум 6 символов)")
