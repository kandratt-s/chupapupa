"""
API эндпоинты для администраторов
"""

import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import (
    AttendanceListResponse,
    AttendanceResponse,
    AttendanceReview,
)
from src.services.attendance_service import AttendanceService
from src.services.auth_service import get_db, require_admin
from src.services.photo_service import PhotoService

router = APIRouter()

# Инициализируем сервисы
photo_service = PhotoService()
attendance_service = AttendanceService(photo_service)


@router.get("/admin/pending", response_model=AttendanceListResponse)
async def get_pending_attendances(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(50, ge=1, le=100, description="Количество записей на странице"),
    current_user: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AttendanceListResponse:
    """Получить список ожидающих рассмотрения заявок"""

    attendances, total = await attendance_service.get_pending_attendances(db, skip, limit)

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


@router.post("/admin/review/{attendance_id}", response_model=AttendanceResponse)
async def submit_review(
    attendance_id: int,
    review_data: AttendanceReview,
    current_user: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AttendanceResponse:
    """Завершить рассмотрение заявки"""

    admin_id = current_user["user_id"]

    try:
        attendance = await attendance_service.submit_review(
            db, attendance_id, admin_id, review_data
        )
        return AttendanceResponse.model_validate(attendance.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке заявки: {str(e)}") from e


@router.get("/admin/pending-count")
async def get_pending_count(
    current_user: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Получить количество ожидающих заявок"""

    count = await attendance_service.get_pending_count(db)
    return {"count": count}
