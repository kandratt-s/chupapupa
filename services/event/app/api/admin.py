"""
Административные API endpoints для Event сервиса.
"""

import math
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud import event_crud
from app.core.dependencies import get_db_session, require_admin
from app.schemas import EventCreate, EventListResponse, EventResponse, EventUpdate

router = APIRouter(tags=["admin"])


@router.post("/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    admin_user: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> EventResponse:
    """
    Создать новое событие (только для администраторов).
    """
    try:
        event = await event_crud.create_event(db, event_data)
        await db.commit()
        return event
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ошибка создания события: {str(e)}"
        ) from e


@router.get("/", response_model=EventListResponse)
async def get_all_events(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(50, ge=1, le=100, description="Количество записей на странице"),
    search: str | None = Query(None, description="Поиск по названию и описанию"),
    search_by_id: int | None = Query(None, description="Поиск по ID события"),
    search_by_date: datetime | None = Query(None, description="Поиск по конкретной дате"),
    date_from: datetime | None = Query(None, description="Дата начала периода"),
    date_to: datetime | None = Query(None, description="Дата окончания периода"),
    include_inactive: bool = Query(False, description="Включить неактивные события"),
    sort_by_date: str = Query(
        "desc", regex="^(asc|desc)$", description="Сортировка по дате (asc/desc)"
    ),
    admin_user: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> EventListResponse:
    """
    Получить все события с расширенными фильтрами (для администраторов).
    """
    # Определяем фильтр активности
    is_active_only = None if include_inactive else True

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


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    admin_user: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> EventResponse:
    """
    Обновить событие (только для администраторов).
    """
    event = await event_crud.update_event(db, event_id, event_data)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Событие с ID {event_id} не найдено"
        )

    try:
        await db.commit()
        return event
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ошибка обновления события: {str(e)}"
        ) from e


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    hard_delete: bool = Query(False, description="Жестко удалить событие"),
    admin_user: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Удалить событие (мягкое или жесткое удаление для администраторов).
    """
    if hard_delete:
        success = await event_crud.hard_delete_event(db, event_id)
    else:
        success = await event_crud.delete_event(db, event_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Событие с ID {event_id} не найдено"
        )

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ошибка удаления события: {str(e)}"
        ) from e
