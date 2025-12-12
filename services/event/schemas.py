"""Event service schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    """Schema for event creation."""

    name: str = Field(..., min_length=3, max_length=255)
    date: datetime
    is_profile: bool = False
    description: str | None = None
    is_active: bool = True


class EventUpdate(BaseModel):
    """Schema for event updates."""

    name: str | None = Field(None, min_length=3, max_length=255)
    date: datetime | None = None
    is_profile: bool | None = None
    description: str | None = None
    is_active: bool | None = None


class EventResponse(BaseModel):
    """Schema for event response."""

    event_id: int = Field(alias="id")
    name: str
    date: datetime
    is_profile: bool
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EventAttendeeCreate(BaseModel):
    """Schema for event attendee creation."""

    event_id: int
    user_id: int


class EventAttendeeResponse(BaseModel):
    """Schema for event attendee response."""

    id: int
    event_id: int
    user_id: int
    status: str
    check_in_time: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
