"""
Pydantic схемы для валидации данных
"""

from datetime import datetime

from pydantic import BaseModel, Field


class AttendanceCreate(BaseModel):
    """Схема для создания заявки"""

    event_id: int = Field(..., description="ID мероприятия")
    notes: str | None = Field(None, max_length=1000, description="Дополнительные заметки")


class AttendanceUpdate(BaseModel):
    """Схема для обновления заявки"""

    notes: str | None = Field(None, max_length=1000, description="Дополнительные заметки")


class AttendanceReview(BaseModel):
    """Схема для рассмотрения заявки администратором"""

    approve: bool = Field(..., description="Одобрить или отклонить заявку")
    notes: str | None = Field(None, max_length=1000, description="Комментарий администратора")
    points: float | None = Field(None, ge=0, description="Количество баллов для начисления (при одобрении)")


class UserInfo(BaseModel):
    """Информация о пользователе"""

    user_id: int
    full_name: str | None = None
    group_name: str | None = None
    points: int | None = None
    file_path: str | None = None


class EventInfo(BaseModel):
    """Информация о мероприятии"""

    event_id: int
    title: str | None = None
    description: str | None = None
    location: str | None = None
    start_time: datetime | None = None


class AttendanceResponse(BaseModel):
    """Схема ответа с информацией о заявке"""

    attendance_id: int
    event_id: int
    user_id: int
    file_path: str | None = None
    is_aproved: bool
    status: str
    reviewed_by: int | None = None
    notes: str | None = None
    created_at: datetime
    checked_at: datetime | None = None

    class Config:
        from_attributes = True


class AttendanceDetailResponse(AttendanceResponse):
    """Детальная информация о заявке для админов"""

    user_info: UserInfo | None = None
    event_info: EventInfo | None = None
    user_photo_url: str | None = None
    attendance_photo_url: str | None = None


class AttendanceListResponse(BaseModel):
    """Схема ответа со списком заявок"""

    attendances: list[AttendanceResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class HealthResponse(BaseModel):
    """Схема ответа health check"""

    service: str = "attendance-service"
    status: str = "healthy"
    database: str = "connected"
    port: int = 8003
    version: str = "2.0.0"
