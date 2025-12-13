"""
Основные API endpoints для Event сервиса.
"""

import math
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud import event_crud
from app.core.dependencies import get_current_user, get_db_session
from app.schemas import EventListResponse, EventResponse

router = APIRouter()


@router.get("/events", response_model=EventListResponse, tags=["events"])
async def get_events(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(50, ge=1, le=100, description="Количество записей на странице"),
    search: str | None = Query(None, description="Поиск по названию и описанию"),
    search_by_id: int | None = Query(None, description="Поиск по ID события"),
    search_by_date: datetime | None = Query(None, description="Поиск по конкретной дате"),
    date_from: datetime | None = Query(None, description="Дата начала периода"),
    date_to: datetime | None = Query(None, description="Дата окончания периода"),
    is_active_only: bool | None = Query(
        None, description="Фильтр по активности (None - все, True - активные, False - неактивные)"
    ),
    sort_by_date: str = Query(
        "desc", regex="^(asc|desc)$", description="Сортировка по дате (asc/desc)"
    ),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> EventListResponse:
    """
    Получить список событий с пагинацией и фильтрацией.
    """
    events, total = await event_crud.get_events_list(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        search_by_id=search_by_id,
        search_by_date=search_by_date,
        date_from=date_from,
        date_to=date_to,
        is_active_only=is_active_only,
        sort_by_date=sort_by_date,
    )

    # Рассчитываем пагинацию
    total_pages = math.ceil(total / limit) if total > 0 else 1
    current_page = (skip // limit) + 1

    return EventListResponse(
        events=events,
        total=total,
        page=current_page,
        per_page=limit,
        total_pages=total_pages,
    )


@router.get("/events/{event_id}", response_model=EventResponse, tags=["events"])
async def get_event(
    event_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> EventResponse:
    """
    Получить событие по ID.
    """
    event = await event_crud.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Событие с ID {event_id} не найдено"
        )

    return event


@router.get("/events/upcoming", response_model=list[EventResponse], tags=["events"])
async def get_upcoming_events(
    limit: int = Query(10, ge=1, le=50, description="Максимальное количество событий"),
    days_ahead: int = Query(30, ge=1, le=365, description="Количество дней вперед"),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[EventResponse]:
    """
    Получить ближайшие события.
    """
    events = await event_crud.get_upcoming_events(
        db=db,
        limit=limit,
        days_ahead=days_ahead,
    )

    return [EventResponse.model_validate(event) for event in events]
