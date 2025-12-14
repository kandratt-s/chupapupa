"""
Главный файл Auth сервиса.
Обрабатывает авторизацию и выдачу JWT токенов.
"""

from datetime import datetime, timedelta
from typing import Any

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from crud import authenticate_user, create_auth, get_auth_by_user_id, update_auth
from database import engine, get_db
from fastapi import Depends, FastAPI, Header, HTTPException, status
from models import Base
from sqlalchemy import text
from schemas import (
    AuthCreate,
    AuthResponse,
    AuthUpdate,
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    Token,
)
from sqlalchemy.orm import Session

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Auth Service API",
    description="Микросервис аутентификации для системы управления событиями ВШЭ",
    version="1.0.0",
)


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========


def get_current_user_from_token(
    authorization: str | None = Header(None), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Получает информацию о текущем пользователе из JWT токена"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization.split(" ")[1]

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        user_id = payload.get("user_id")
        role = payload.get("role")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Проверяем, что пользователь существует в Auth таблице
        auth_record = get_auth_by_user_id(db, user_id)
        if not auth_record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return {"user_id": user_id, "role": role, "auth_record": auth_record}

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from None


# ========== ПУБЛИЧНЫЕ ЭНДПОИНТЫ ==========


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    """Базовый health check"""
    return {"service": "auth-service", "status": "running", "version": "1.0.0"}


@app.post("/login", response_model=Token, tags=["auth"])
def login(login_data: LoginRequest, db: Session = Depends(get_db)) -> Token:
    """
    Авторизация пользователя.
    Проверяет user_id и пароль, возвращает JWT токены.
    """
    # Аутентифицируем пользователя
    auth_record = authenticate_user(db, login_data.user_id, login_data.password)
    if not auth_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user_id or password"
        )

    # Создаем данные для токена
    token_data = {"user_id": auth_record.user_id, "role": auth_record.role}

    # Создаем токены
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)

    refresh_token = create_refresh_token(data=token_data, expires_delta=refresh_token_expires)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@app.post("/refresh", response_model=Token, tags=["auth"])
def refresh_token(refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)) -> Token:
    """
    Обновление access токена по refresh токену.
    """
    try:
        # Декодируем refresh токен
        payload = decode_token(refresh_data.refresh_token)

        # Проверяем тип токена
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Проверяем, что пользователь существует
        auth_record = get_auth_by_user_id(db, user_id)
        if not auth_record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        # Создаем новые токены
        token_data = {"user_id": auth_record.user_id, "role": auth_record.role}

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        access_token = create_access_token(data=token_data, expires_delta=access_token_expires)

        new_refresh_token = create_refresh_token(
            data=token_data, expires_delta=refresh_token_expires
        )

        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from None


# ========== ПОЛЬЗОВАТЕЛЬСКИЕ ЭНДПОИНТЫ ==========


@app.put("/change-password", tags=["users"])
def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict[str, Any] = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Смена пароля текущим пользователем.

    Пользователь должен предоставить:
    - Текущий пароль для подтверждения
    - Новый пароль

    Требует валидный JWT токен в заголовке Authorization.
    """
    from auth import get_password_hash, verify_password

    auth_record = current_user["auth_record"]

    # Проверяем текущий пароль
    if not verify_password(password_data.current_password, auth_record.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )

    # Хешируем новый пароль
    new_password_hash = get_password_hash(password_data.new_password)

    # Обновляем пароль в базе данных
    auth_record.password_hash = new_password_hash
    db.commit()

    return {"message": "Password changed successfully"}


# ========== АДМИНСКИЕ ЭНДПОИНТЫ ==========


@app.post("/create", response_model=AuthResponse, tags=["admin"])
def create_auth_record(auth_data: AuthCreate, db: Session = Depends(get_db)) -> AuthResponse:
    """
    Создание записи аутентификации для существующего пользователя.
    ВНИМАНИЕ: user_id должен уже существовать в таблице users из userStatistic!

    Этот эндпоинт используется Admin сервисом и не требует токенов,
    так как Auth является базовым сервисом в архитектуре.
    """
    try:
        auth_record = create_auth(db, auth_data)
        return AuthResponse(
            user_id=auth_record.user_id,
            role=auth_record.role,
            created_at=auth_record.created_at.isoformat(),
            updated_at=auth_record.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@app.put("/{user_id}", response_model=AuthResponse, tags=["admin"])
def update_auth_record(
    user_id: int, auth_data: AuthUpdate, db: Session = Depends(get_db)
) -> AuthResponse:
    """
    Обновление записи аутентификации.
    Используется Admin сервисом для управления пользователями.
    """
    auth_record = update_auth(db, user_id, auth_data)
    if not auth_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auth record for user_id {user_id} not found",
        )

    return AuthResponse(
        user_id=auth_record.user_id,
        role=auth_record.role,
        created_at=auth_record.created_at.isoformat(),
        updated_at=auth_record.updated_at.isoformat(),
    )


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, Any]:
    """Проверка здоровья сервиса"""
    db_status = "disconnected"
    
    try:
        # Простая проверка подключения к БД через SQLAlchemy
        db = next(get_db())
        result = db.execute(text("SELECT 1"))
        if result:
            db_status = "connected"
        db.close()
    except Exception:
        db_status = "disconnected"
    
    return {
        "service": "auth-service",
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "port": 8001,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/{user_id}", response_model=AuthResponse, tags=["admin"])
def get_auth_record(user_id: int, db: Session = Depends(get_db)) -> AuthResponse:
    """
    Получение информации об аутентификации пользователя.
    Используется другими сервисами для проверки ролей.
    """
    auth_record = get_auth_by_user_id(db, user_id)
    if not auth_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auth record for user_id {user_id} not found",
        )

    return AuthResponse(
        user_id=auth_record.user_id,
        role=auth_record.role,
        created_at=auth_record.created_at.isoformat(),
        updated_at=auth_record.updated_at.isoformat(),
    )


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, Any]:
    """Health check эндпоинт для мониторинга с проверкой БД"""
    db_status = "disconnected"
    
    try:
        # Простая проверка подключения к БД через SQLAlchemy
        db = next(get_db())
        result = db.execute(text("SELECT 1"))
        if result:
            db_status = "connected"
        db.close()
    except Exception:
        db_status = "disconnected"
    
    return {
        "service": "auth-service",
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "port": 8001,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }
