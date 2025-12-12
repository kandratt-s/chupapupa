"""Attendance service schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AttendanceCreate(BaseModel):
    """Schema for attendance creation."""

    user_id: int
    event_id: int
    photo_path: str | None = Field(None, max_length=500)  # путь к фото
    is_approved: bool = False  # по умолчанию не подтверждено


class AttendanceUpdate(BaseModel):
    """Schema for attendance updates."""

    photo_path: str | None = Field(None, max_length=500)
    is_approved: bool | None = None


class AttendanceResponse(BaseModel):
    """Schema for attendance response."""

    attendance_id: int = Field(alias="id")
    user_id: int
    event_id: int
    photo_path: str | None
    is_approved: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
