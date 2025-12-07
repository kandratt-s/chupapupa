from sqlalchemy.orm import Session
from sqlalchemy import or_
from models import User
from schemas import UserCreateByAdmin, UserUpdate
from auth import get_password_hash, verify_password
from datetime import datetime


def get_user_by_email(db: Session, email: str):
    """Получает пользователя по email"""
    return db.query(User).filter(User.hse_email == email).first()


def get_user_by_id(db: Session, user_id: int):
    """Получает пользователя по ID"""
    return db.query(User).filter(User.id == user_id).first()


def create_user_by_admin(db: Session, user_data: UserCreateByAdmin, admin_id: int):
    """Админ создает нового пользователя"""
    # Проверяем, существует ли пользователь с таким email
    existing_user = get_user_by_email(db, user_data.hse_email)
    if existing_user:
        raise ValueError("User with this email already exists")

    # Хешируем пароль
    hashed_password = get_password_hash(user_data.password)

    # Создаем пользователя
    user = User(
        hse_email=user_data.hse_email,
        telegram_id=user_data.telegram_id,
        role=user_data.role.value,  # Используем .value для Enum
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        student_id=user_data.student_id,
        profile_photo=user_data.profile_photo,
        created_by=admin_id,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, user_data: UserUpdate):
    """Обновляет пользователя"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    update_dict = user_data.dict(exclude_unset=True)

    # Если обновляется пароль - хешируем его
    if "password" in update_dict and update_dict["password"]:
        update_dict["hashed_password"] = get_password_hash(update_dict.pop("password"))

    # Если обновляется роль - используем .value для Enum
    if "role" in update_dict and update_dict["role"]:
        update_dict["role"] = update_dict["role"].value

    # Обновляем поля
    for field, value in update_dict.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str):
    """Аутентифицирует пользователя"""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def get_all_users(db: Session, skip: int = 0, limit: int = 100):
    """Получает всех пользователей"""
    return db.query(User).offset(skip).limit(limit).all()


def deactivate_user(db: Session, user_id: int):
    """Деактивирует пользователя"""
    user = get_user_by_id(db, user_id)
    if user:
        user.is_active = False
        db.commit()
        return True
    return False