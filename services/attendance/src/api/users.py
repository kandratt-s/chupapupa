"""
API эндпоинты для пользователей
"""

import math
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AttendanceRecord
from src.models.schemas import AttendanceCreate, AttendanceListResponse, AttendanceResponse
from src.services.attendance_service import AttendanceService
from src.services.auth_service import get_current_user, get_db
from src.services.photo_service import PhotoService

router = APIRouter()

# Инициализируем сервисы
photo_service = PhotoService()
attendance_service = AttendanceService(photo_service)


@router.post("/attendances", response_model=AttendanceResponse)
async def create_attendance(
    event_id: int = Form(..., description="ID мероприятия"),
    notes: str = Form(None, description="Дополнительные заметки"),
    photo: UploadFile = File(..., description="Файл с мероприятия (фото или PDF)"),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttendanceResponse:
    """Создать заявку на посещаемость с файлом (фото или PDF документ)"""

    user_id = current_user["user_id"]

    # Создаем объект с данными
    attendance_data = AttendanceCreate(event_id=event_id, notes=notes)

    # Создаем заявку
    attendance = await attendance_service.create_attendance(db, user_id, attendance_data, photo)

    return AttendanceResponse.model_validate(attendance.to_dict())


@router.get("/attendances", response_model=AttendanceListResponse)
async def get_my_attendances(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(50, ge=1, le=100, description="Количество записей на странице"),
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttendanceListResponse:
    """Получить список своих заявок"""

    user_id = current_user["user_id"]

    attendances, total = await attendance_service.get_user_attendances(db, user_id, skip, limit)

    # Рассчитываем пагинацию
    total_pages = math.ceil(total / limit) if total > 0 else 1
    page = (skip // limit) + 1

    return AttendanceListResponse(
        attendances=[AttendanceResponse.model_validate(att.to_dict()) for att in attendances],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/attendances/{attendance_id}", response_model=AttendanceResponse)
async def get_attendance_by_id(
    attendance_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttendanceResponse:
    """Получить заявку по ID (только свою)"""

    user_id = current_user["user_id"]

    attendance = await db.get(AttendanceRecord, attendance_id)
    if not attendance:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    if attendance.user_id != user_id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    return AttendanceResponse.model_validate(attendance.to_dict())
