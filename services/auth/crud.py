"""
CRUD операции для Auth сервиса.
"""

import httpx
from sqlalchemy.orm import Session
from models import Auth
from schemas import AuthCreate, AuthUpdate
from auth import get_password_hash, verify_password
from typing import Optional


def get_auth_by_user_id(db: Session, user_id: int) -> Optional[Auth]:
    """Получает запись аутентификации по user_id"""
    return db.query(Auth).filter(Auth.user_id == user_id).first()


def create_auth(db: Session, auth_data: AuthCreate) -> Auth:
    """Создает новую запись аутентификации"""
    # Проверяем, что пользователь с таким user_id не существует
    existing_auth = get_auth_by_user_id(db, auth_data.user_id)
    if existing_auth:
        raise ValueError(f"Auth record for user_id {auth_data.user_id} already exists")
    
    # Хешируем пароль
    hashed_password = get_password_hash(auth_data.password)
    
    # Создаем запись
    auth_record = Auth(
        user_id=auth_data.user_id,
        password_hash=hashed_password,
        role=auth_data.role.value
    )
    
    db.add(auth_record)
    db.commit()
    db.refresh(auth_record)
    return auth_record


def update_auth(db: Session, user_id: int, auth_data: AuthUpdate) -> Optional[Auth]:
    """Обновляет запись аутентификации"""
    auth_record = get_auth_by_user_id(db, user_id)
    if not auth_record:
        return None
    
    # Собираем данные для обновления
    update_dict = {}
    if auth_data.password is not None:
        update_dict["password_hash"] = get_password_hash(auth_data.password)
    if auth_data.role is not None:
        update_dict["role"] = auth_data.role.value

    # Обновляем поля
    for field, value in update_dict.items():
        setattr(auth_record, field, value)

    db.commit()
    db.refresh(auth_record)
    return auth_record


def authenticate_user(db: Session, user_id: int, password: str) -> Optional[Auth]:
    """Аутентифицирует пользователя по user_id и паролю"""
    auth_record = get_auth_by_user_id(db, user_id)
    if not auth_record:
        return None
    if not verify_password(password, auth_record.password_hash):
        return None
    return auth_record


async def authenticate_user_by_email(db: Session, email: str, password: str) -> Optional[Auth]:
    """Аутентифицирует пользователя по email и паролю"""
    # Запрашиваем пользователя по email из userStatistic сервиса
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://user-statistic-service:8006/users/by-email",
                params={"email": email},
                timeout=5.0
            )
            
            if response.status_code != 200:
                return None
                
            user_data = response.json()
            user_id = user_data.get("user_id")
            
            if not user_id:
                return None
                
            # Проверяем пароль через существующую функцию
            return authenticate_user(db, user_id, password)
            
    except (httpx.RequestError, httpx.TimeoutException):
        return None