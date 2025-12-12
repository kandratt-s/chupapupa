"""User Statistic service schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserStatisticCreate(BaseModel):
    """Schema for user statistic creation."""

    user_id: int
    events_attended: int = 0
    events_organized: int = 0
    total_hours: float = 0.0
    average_rating: float | None = None
    last_activity: str | None = None


class UserStatisticUpdate(BaseModel):
    """Schema for user statistic updates."""

    events_attended: int | None = None
    events_organized: int | None = None
    total_hours: float | None = None
    average_rating: float | None = None
    last_activity: str | None = None


class UserStatisticResponse(BaseModel):
    """Schema for user statistic response."""

    id: int
    user_id: int
    events_attended: int
    events_organized: int
    total_hours: float
    average_rating: float | None
    last_activity: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
