"""
Pydantic схемы для Event сервиса.
"""

from datetime import datetime

from pydantic import BaseModel, Field

# ========== Event SCHEMAS ==========


class EventBase(BaseModel):
    """Базовая схема события."""

    name: str = Field(..., min_length=1, max_length=255, description="Название события")
    date: datetime = Field(..., description="Дата и время события")
    profilnoe: bool = Field(False, description="Профильное мероприятие")
    opisanie: str | None = Field(None, description="Описание события")
    active: bool = Field(True, description="Активность события")


class EventCreate(EventBase):
    """Схема для создания события."""

    pass


class EventUpdate(BaseModel):
    """Схема для обновления события."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Название события")
    date: datetime | None = Field(None, description="Дата и время события")
    profilnoe: bool | None = Field(None, description="Профильное мероприятие")
    opisanie: str | None = Field(None, description="Описание события")
    active: bool | None = Field(None, description="Активность события")


class EventResponse(EventBase):
    """Схема ответа с информацией о событии."""

    event_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Схема ответа со списком событий и пагинацией."""

    events: list[EventResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# ========== HEALTH CHECK SCHEMAS ==========


class HealthResponse(BaseModel):
    """Схема ответа health check."""

    service: str
    status: str
    database: str
    port: int
    version: str
