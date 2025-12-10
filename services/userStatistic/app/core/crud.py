"""
CRUD (Create, Read, Update, Delete) операции для работы с пользователями.
Содержит всю бизнес-логику для взаимодействия с таблицей пользователей.
Обновлено для работы с английскими названиями полей.
"""

from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import User
from app.schemas import UserCreate, UserUpdate


class UserCRUD:
    """
    Класс для выполнения CRUD операций с пользователями.
    Инкапсулирует всю логику работы с базой данных.
    """

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """
        Получить пользователя по user_id.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя

        Returns:
            User или None, если пользователь не найден
        """
        return db.query(User).filter(User.user_id == user_id).first()

    @staticmethod
    def get_user_by_tg_id(db: Session, tg_id: str) -> Optional[User]:
        """
        Получить пользователя по Telegram ID.

        Args:
            db: Сессия базы данных
            tg_id: Telegram ID пользователя

        Returns:
            User или None, если пользователь не найден
        """
        return db.query(User).filter(User.tg_id == tg_id).first()

    @staticmethod
    def get_user_by_tg_name(db: Session, tg_name: str) -> Optional[User]:
        """
        Получить пользователя по Telegram username.

        Args:
            db: Сессия базы данных
            tg_name: Telegram username (с @ или без)

        Returns:
            User или None, если пользователь не найден
        """
        # Приводим к единому формату с @
        if tg_name and not tg_name.startswith("@"):
            tg_name = "@" + tg_name
        return db.query(User).filter(User.tg_name == tg_name).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """
        Получить пользователя по email.

        Args:
            db: Сессия базы данных
            email: Электронная почта пользователя

        Returns:
            User или None, если пользователь не найден
        """
        return db.query(User).filter(User.hs_email == email).first()

    @staticmethod
    def get_users_list(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        group_filter: Optional[str] = None,
        is_active_only: bool = False,
    ) -> Tuple[List[User], int]:
        """
        Получить список пользователей с пагинацией и поиском.

        Args:
            db: Сессия базы данных
            skip: Количество записей для пропуска (offset)
            limit: Максимальное количество записей
            search: Строка поиска по ФИО, группе или telegram
            group_filter: Фильтр по конкретной группе
            is_active_only: Фильтр только активных пользователей

        Returns:
            Tuple[List[User], int]: Список пользователей и общее количество
        """
        query = db.query(User)

        # Фильтр по группе
        if group_filter:
            query = query.filter(User.group_name.ilike(f"%{group_filter}%"))

        # Поиск по различным полям
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    User.last_name.ilike(search_pattern),
                    User.first_name.ilike(search_pattern),
                    User.middle_name.ilike(search_pattern),
                    User.group_name.ilike(search_pattern),
                    User.tg_name.ilike(search_pattern),
                    User.hs_email.ilike(search_pattern),
                )
            )

        # Получаем общее количество для пагинации
        total = query.count()

        # Применяем сортировку и пагинацию
        users = (
            query.order_by(User.last_name, User.first_name)
            .offset(skip)
            .limit(limit)
            .all()
        )

        return users, total

    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        """
        Создать нового пользователя.

        Args:
            db: Сессия базы данных
            user_data: Данные для создания пользователя

        Returns:
            User: Созданный пользователь

        Raises:
            ValueError: Если пользователь с такими данными уже существует
        """
        # Проверка уникальности email
        existing_email = UserCRUD.get_user_by_email(db, user_data.hs_email)
        if existing_email:
            raise ValueError(
                f"Пользователь с email '{user_data.hs_email}' уже существует"
            )

        # Проверка уникальности Telegram ID
        if user_data.tg_id:
            existing_tg_id = UserCRUD.get_user_by_tg_id(db, user_data.tg_id)
            if existing_tg_id:
                raise ValueError(
                    f"Пользователь с Telegram ID '{user_data.tg_id}' уже существует"
                )

        # Создание пользователя
        db_user = User(
            last_name=user_data.last_name,
            first_name=user_data.first_name,
            middle_name=user_data.middle_name,
            group_name=user_data.group_name,
            hs_email=user_data.hs_email,
            tg_id=user_data.tg_id,
            tg_name=user_data.tg_name,
            practice_points=user_data.practice_points,
            photo_path=user_data.photo_path,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return db_user

    @staticmethod
    def update_user(db: Session, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """
        Обновить данные пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя для обновления
            user_data: Новые данные пользователя

        Returns:
            User или None, если пользователь не найден

        Raises:
            ValueError: Если новые данные конфликтуют с существующими
        """
        user = UserCRUD.get_user_by_id(db, user_id)
        if not user:
            return None

        # Преобразуем данные в словарь, исключая None значения
        update_data = user_data.dict(exclude_unset=True)

        # Проверка уникальности email (если меняется)
        if "hs_email" in update_data and update_data["hs_email"]:
            existing = UserCRUD.get_user_by_email(db, update_data["hs_email"])
            if existing and existing.user_id != user_id:
                raise ValueError(
                    f"Пользователь с email '{update_data['hs_email']}' уже существует"
                )

        # Проверка уникальности Telegram ID (если меняется)
        if "tg_id" in update_data and update_data["tg_id"]:
            existing = UserCRUD.get_user_by_tg_id(db, update_data["tg_id"])
            if existing and existing.user_id != user_id:
                raise ValueError(
                    f"Пользователь с Telegram ID '{update_data['tg_id']}' уже существует"
                )

        # Обновляем поля пользователя
        for field, value in update_data.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def update_user_points(db: Session, user_id: int, points: float) -> Optional[User]:
        """
        Обновить баллы пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            points: Новое количество баллов

        Returns:
            User или None, если пользователь не найден
        """
        user = UserCRUD.get_user_by_id(db, user_id)
        if not user:
            return None

        user.practice_points = points  # type: ignore[assignment]
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        """
        Удалить пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя для удаления

        Returns:
            bool: True, если пользователь был удален, False если не найден
        """
        user = UserCRUD.get_user_by_id(db, user_id)
        if not user:
            return False

        db.delete(user)
        db.commit()

        return True

    @staticmethod
    def get_users_by_group(db: Session, group_name: str) -> List[User]:
        """
        Получить всех пользователей из конкретной группы.

        Args:
            db: Сессия базы данных
            group_name: Название группы

        Returns:
            List[User]: Список пользователей в группе
        """
        return db.query(User).filter(User.group_name == group_name).all()

    @staticmethod
    def get_group_statistics(db: Session) -> List[Dict[str, Any]]:
        """
        Получить статистику по группам.

        Args:
            db: Сессия базы данных

        Returns:
            List[Dict[str, Any]]: Статистика по группам
        """
        from sqlalchemy import func

        result = (
            db.query(
                User.group_name,
                func.count(User.user_id).label("total_users"),
                func.avg(User.practice_points).label("avg_points"),
                func.max(User.practice_points).label("max_points"),
                func.min(User.practice_points).label("min_points"),
            )
            .group_by(User.group_name)
            .all()
        )

        return [
            {
                "group_name": row.group_name,
                "total_users": row.total_users,
                "avg_points": float(row.avg_points) if row.avg_points else 0.0,
                "max_points": row.max_points,
                "min_points": row.min_points,
            }
            for row in result
        ]


# Создаем экземпляр для использования в других модулях
user_crud = UserCRUD()
