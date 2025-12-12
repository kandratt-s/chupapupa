from fastapi import Depends, FastAPI, HTTPException, status
from models import Event
from repositories import EventRepository
from schemas import EventCreate, EventResponse, EventUpdate
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db

app = FastAPI(title="Event Service", description="Event management service", version="1.0.0")


# ==================== Health Check ====================
@app.get("/health", tags=["health"])
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Check service health."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        ) from err


# ==================== Event Endpoints ====================
@app.post(
    "/events", response_model=EventResponse, tags=["events"], status_code=status.HTTP_201_CREATED
)
async def create_event(
    event_data: EventCreate, db: AsyncSession = Depends(get_db)
) -> EventResponse:
    """Create a new event."""
    repo = EventRepository(db, Event)

    event = await repo.create(
        name=event_data.name,
        date=event_data.date,
        is_profile=event_data.is_profile,
        description=event_data.description,
        is_active=event_data.is_active,
    )

    await repo.commit()
    return event


@app.get("/events", response_model=list[EventResponse], tags=["events"])
async def get_events(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Event]:
    """Get all events with pagination."""
    repo = EventRepository(db, Event)
    events: list[Event] = await repo.get_all(skip=skip, limit=limit)
    return events


@app.get("/events/active", response_model=list[EventResponse], tags=["events"])
async def get_active_events(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Event]:
    """Get all active events."""
    repo = EventRepository(db, Event)
    events: list[Event] = await repo.get_active_events(skip=skip, limit=limit)
    return events


@app.get("/events/upcoming", response_model=list[EventResponse], tags=["events"])
async def get_upcoming_events(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Event]:
    """Get upcoming events."""
    repo = EventRepository(db, Event)
    events: list[Event] = await repo.get_upcoming_events(skip=skip, limit=limit)
    return events


@app.get("/events/past", response_model=list[EventResponse], tags=["events"])
async def get_past_events(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Event]:
    """Get past events."""
    repo = EventRepository(db, Event)
    events: list[Event] = await repo.get_past_events(skip=skip, limit=limit)
    return events


@app.get("/events/profile", response_model=list[EventResponse], tags=["events"])
async def get_profile_events(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Event]:
    """Get profile events."""
    repo = EventRepository(db, Event)
    events: list[Event] = await repo.get_profile_events(skip=skip, limit=limit)
    return events


@app.get("/events/{event_id}", response_model=EventResponse, tags=["events"])
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)) -> EventResponse:
    """Get event by ID."""
    repo = EventRepository(db, Event)
    event = await repo.get_by_id(event_id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return event


@app.put("/events/{event_id}", response_model=EventResponse, tags=["events"])
async def update_event(
    event_id: int, event_data: EventUpdate, db: AsyncSession = Depends(get_db)
) -> EventResponse:
    """Update event."""
    repo = EventRepository(db, Event)

    event = await repo.get_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    update_data = event_data.model_dump(exclude_unset=True)
    updated_event = await repo.update(event_id, **update_data)

    await repo.commit()
    return updated_event


@app.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["events"])
async def delete_event(event_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete event."""
    repo = EventRepository(db, Event)

    deleted = await repo.delete(event_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    await repo.commit()
