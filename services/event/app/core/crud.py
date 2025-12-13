"""
CRUD (Create, Read, Update, Delete) операции для работы с событиями.
"""

from datetime import datetime

from sqlalchemy import and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Event
from app.schemas import EventCreate, EventUpdate


class EventCRUD:
    """
    Класс для выполнения CRUD операций с событиями.
    """

    @staticmethod
    async def get_event_by_id(db: AsyncSession, event_id: int) -> Event | None:
        """
        Получить событие по ID.
        """
        result = await db.execute(select(Event).filter(Event.event_id == event_id))
        return result.scalars().first()

    @staticmethod
    async def get_events_list(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        search_by_id: int | None = None,
        search_by_date: datetime | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        is_active_only: bool | None = None,
        sort_by_date: str = "desc",  # "asc" или "desc"
    ) -> tuple[list[Event], int]:
        """
        Получить список событий с расширенной фильтрацией и пагинацией.
        """
        query = select(Event)

        # Фильтр по активности (None = все, True = только активные, False = только неактивные)
        if is_active_only is not None:
            query = query.filter(Event.active == is_active_only)

        # Поиск по ID
        if search_by_id is not None:
            query = query.filter(Event.event_id == search_by_id)

        # Поиск по конкретной дате
        if search_by_date:
            # Поиск по дню (игнорируем время)
            query = query.filter(func.date(Event.date) == search_by_date.date())

        # Поиск в диапазоне дат
        if date_from:
            query = query.filter(Event.date >= date_from)
        if date_to:
            query = query.filter(Event.date <= date_to)

        # Текстовый поиск по названию и описанию
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Event.name.ilike(search_pattern),
                    Event.opisanie.ilike(search_pattern),
                )
            )

        # Общее количество
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Применяем сортировку
        if sort_by_date.lower() == "asc":
            query = query.order_by(Event.date.asc())
        else:
            query = query.order_by(Event.date.desc())

        # Применяем пагинацию
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        events = result.scalars().all()

        return list(events), total

    @staticmethod
    async def create_event(db: AsyncSession, event_data: EventCreate) -> Event:
        """
        Создать новое событие.
        """
        event_dict = event_data.model_dump()
        event = Event(**event_dict)

        db.add(event)
        await db.flush()
        await db.refresh(event)

        return event

    @staticmethod
    async def update_event(
        db: AsyncSession, event_id: int, event_data: EventUpdate
    ) -> Event | None:
        """
        Обновить существующее событие.
        """
        event = await EventCRUD.get_event_by_id(db, event_id)
        if not event:
            return None

        # Преобразуем данные в словарь, исключая None значения
        update_data = event_data.model_dump(exclude_unset=True)

        # Обновляем поля события
        for field, value in update_data.items():
            setattr(event, field, value)

        await db.flush()
        await db.refresh(event)

        return event

    @staticmethod
    async def delete_event(db: AsyncSession, event_id: int) -> bool:
        """
        Удалить событие (мягкое удаление - деактивация).
        """
        event = await EventCRUD.get_event_by_id(db, event_id)
        if not event:
            return False

        event.active = False
        await db.flush()

        return True

    @staticmethod
    async def hard_delete_event(db: AsyncSession, event_id: int) -> bool:
        """
        Жестко удалить событие из БД.
        """
        event = await EventCRUD.get_event_by_id(db, event_id)
        if not event:
            return False

        await db.delete(event)
        await db.flush()

        return True

    @staticmethod
    async def get_upcoming_events(
        db: AsyncSession, limit: int = 10, days_ahead: int = 30
    ) -> list[Event]:
        """
        Получить ближайшие события.
        """
        from datetime import timedelta

        now = datetime.utcnow()
        future_date = now + timedelta(days=days_ahead)

        query = (
            select(Event)
            .filter(
                and_(
                    Event.active,
                    Event.date >= now,
                    Event.date <= future_date,
                )
            )
            .order_by(Event.date.asc())
            .limit(limit)
        )

        result = await db.execute(query)
        return list(result.scalars().all())


# Создаем экземпляр для использования в других модулях
event_crud = EventCRUD()
