from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List

from database import engine, get_db
from models import Base, User
from schemas import (
    UserCreateByAdmin, UserResponse, Token,
    LoginRequest, LoginResponse, RefreshTokenRequest,
    UserUpdate
)
from crud import *
from auth import *
from dependencies import *

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HSE Event Management API",
    description="API для управления мероприятиями ВШЭ с авторизацией через админов",
    version="1.0.0"
)


# ========== ПУБЛИЧНЫЕ ЭНДПОИНТЫ ==========

@app.post("/login", response_model=Token)
async def login(
        login_data: LoginRequest,
        db: Session = Depends(get_db)
):
    """
    Вход в систему для существующих пользователей
    (пользователей создают админы)
    """
    # Аутентифицируем пользователя
    user = authenticate_user(db, login_data.hse_email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Создаем токены
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        data={"sub": user.hse_email},
        expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(
        data={"sub": user.hse_email},
        expires_delta=refresh_token_expires
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user
    )


@app.post("/refresh", response_model=Token)
async def refresh_token(
        refresh_data: RefreshTokenRequest,
        db: Session = Depends(get_db)
):
    """
    Обновление access токена
    """
    try:
        # Декодируем refresh токен
        payload = decode_token(refresh_data.refresh_token)
        email = payload.get("sub")
        token_type = payload.get("type")

        if token_type != "refresh" or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Проверяем, существует ли пользователь
        user = get_user_by_email(db, email)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        # Создаем новый access токен
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={"sub": user.hse_email},
            expires_delta=access_token_expires
        )

        return Token(
            access_token=new_access_token,
            refresh_token=refresh_data.refresh_token,  # Старый refresh токен
            user=user
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


# ========== ЭНДПОИНТЫ ДЛЯ АДМИНОВ ==========

@app.post("/admin/users", response_model=UserResponse)
async def create_user_by_admin(
        user_data: UserCreateByAdmin,
        db: Session = Depends(get_db),
        admin: User = Depends(require_admin)  # Только админы могут создавать пользователей
):
    """
    Админ создает нового пользователя
    """
    try:
        user = create_user_by_admin(db, user_data, admin.id)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/admin/users", response_model=List[UserResponse])
async def get_all_users_admin(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        admin: User = Depends(require_admin)
):
    """
    Админ получает список всех пользователей
    """
    users = get_all_users(db, skip, limit)
    return users


@app.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user_admin(
        user_id: int,
        user_data: UserUpdate,
        db: Session = Depends(get_db),
        admin: User = Depends(require_admin)
):
    """
    Админ обновляет данные пользователя
    """
    user = update_user(db, user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@app.delete("/admin/users/{user_id}")
async def deactivate_user_admin(
        user_id: int,
        db: Session = Depends(get_db),
        admin: User = Depends(require_admin)
):
    """
    Админ деактивирует пользователя
    """
    success = deactivate_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "User deactivated successfully"}


# ========== ОБЩИЕ ЭНДПОИНТЫ (для всех аутентифицированных) ==========

@app.get("/me", response_model=UserResponse)
async def get_current_user_info(
        current_user: User = Depends(get_current_active_user)
):
    """
    Получить информацию о текущем пользователе
    """
    return current_user


@app.put("/me", response_model=UserResponse)
async def update_current_user(
        user_data: UserUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Обновить информацию о себе
    (нельзя менять email и роль)
    """
    # Запрещаем менять email и роль через этот эндпоинт
    update_data = user_data.dict(exclude_unset=True)
    if "hse_email" in update_data or "role" in update_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change email or role"
        )

    user = update_user(db, current_user.id, user_data)
    return user


@app.get("/protected")
async def protected_route(
        current_user: User = Depends(get_current_active_user)
):
    """
    Защищенный маршрут (для всех авторизованных)
    """
    return {
        "message": f"Hello, {current_user.full_name}!",
        "role": current_user.role,
        "email": current_user.hse_email
    }


# ========== РОЛЕВЫЕ ЭНДПОИНТЫ ==========

@app.get("/staff/dashboard")
async def staff_dashboard(
        staff: User = Depends(require_staff)  # Только сотрудники
):
    """
    Панель управления для сотрудников
    """
    return {
        "message": "Staff dashboard",
        "user": staff.full_name,
        "permissions": ["create_events", "view_statistics"]
    }


@app.get("/admin/dashboard")
async def admin_dashboard(
        admin: User = Depends(require_admin)  # Только админы
):
    """
    Панель управления для админов
    """
    return {
        "message": "Admin dashboard",
        "user": admin.full_name,
        "permissions": ["manage_users", "manage_events", "view_all"]
    }


@app.get("/student/dashboard")
async def student_dashboard(
        student: User = Depends(require_role("student"))  # Только студенты
):
    """
    Панель для студентов
    """
    return {
        "message": "Student dashboard",
        "user": student.full_name,
        "student_id": student.student_id,
        "permissions": ["check_in_events", "view_progress"]
    }


# ========== HEALTH CHECKS ==========

@app.get("/")
async def root():
    return {"message": "HSE Event Management API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}


# from fastapi import FastAPI
# from datetime import datetime
#
# app = FastAPI()
#
# @app.get("/")
# def home():
#     return {"message": "Сервер работает!", "time": datetime.now().isoformat()}
#
# @app.get("/test")
# def test():
#     return {"status": "OK"}

