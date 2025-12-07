from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    STAFF = "staff"
    ADMIN = "admin"


# ========== USER SCHEMAS ==========

# Для логина
class LoginRequest(BaseModel):
    hse_email: EmailStr
    password: str


# Для создания пользователя админом
class UserCreateByAdmin(BaseModel):
    hse_email: EmailStr
    telegram_id: Optional[str] = None
    role: UserRole = UserRole.STUDENT
    password: str = Field(..., min_length=6, description="Минимум 6 символов")
    full_name: str = Field(..., min_length=2, description="ФИО пользователя")
    student_id: Optional[str] = None
    profile_photo: Optional[str] = None


# Для обновления пользователя
class UserUpdate(BaseModel):
    telegram_id: Optional[str] = None
    role: Optional[UserRole] = None
    password: Optional[str] = Field(None, min_length=6)
    full_name: Optional[str] = Field(None, min_length=2)
    student_id: Optional[str] = None
    profile_photo: Optional[str] = None
    is_active: Optional[bool] = None


# Ответ с информацией о пользователе
class UserResponse(BaseModel):
    id: int
    hse_email: str
    telegram_id: Optional[str]
    role: str
    full_name: str
    student_id: Optional[str]
    is_active: bool
    profile_photo: Optional[str]
    created_at: datetime
    created_by: Optional[int]

    class Config:
        from_attributes = True


# Список пользователей
class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    skip: int
    limit: int


# ========== TOKEN SCHEMAS ==========

# Для запроса обновления токена
class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Токены + информация о пользователе
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# Только токены (без user)
class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Данные в payload токена
class TokenPayload(BaseModel):
    sub: Optional[str] = None  # email пользователя
    exp: Optional[int] = None  # время истечения
    type: Optional[str] = None  # access/refresh
    jti: Optional[str] = None  # идентификатор токена


# ========== RESPONSE SCHEMAS ==========

class LoginResponse(BaseModel):
    user: UserResponse
    tokens: Token


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


# ========== HEALTH CHECK ==========

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    database: str = "connected"
    service: str = "auth"