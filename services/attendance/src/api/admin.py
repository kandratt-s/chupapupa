"""
API эндпоинты для администраторов
"""

import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import (
    AttendanceDetailResponse,
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


@router.get("/detail/{attendance_id}", response_model=AttendanceDetailResponse)
async def get_attendance_detail(
    attendance_id: int,
    current_user: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AttendanceDetailResponse:
    """Получить детализированную информацию о заявке с фотографиями пользователя"""

    try:
        attendance = await attendance_service.get_attendance_by_id(db, attendance_id)
        if not attendance:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        # Создаем базовый ответ
        response_data = AttendanceResponse.model_validate(attendance.to_dict())

        # Добавляем URLs для фотографий
        user_photo_url = photo_service.get_user_photo_url(attendance.user_id)
        attendance_photo_url = None

        if attendance.photo_path:
            import os

            filename = os.path.basename(attendance.photo_path)
            attendance_photo_url = f"/static/attendances/{filename}"

        return AttendanceDetailResponse(
            **response_data.model_dump(),
            user_photo_url=user_photo_url,
            attendance_photo_url=attendance_photo_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении заявки: {str(e)}") from e


@router.get("/pending", response_model=AttendanceListResponse)
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


@router.post("/review/{attendance_id}", response_model=AttendanceResponse)
async def submit_review(
    attendance_id: int,
    review_data: AttendanceReview,
    request: Request,
    current_user: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AttendanceResponse:
    """Завершить рассмотрение заявки"""

    admin_id = current_user["user_id"]

    try:
        attendance = await attendance_service.submit_review(
            db,
            attendance_id,
            admin_id,
            review_data,
            auth_header=request.headers.get("authorization"),
        )
        return AttendanceResponse.model_validate(attendance.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке заявки: {str(e)}") from e


@router.get("/pending-count")
async def get_pending_count(
    current_user: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Получить количество ожидающих заявок"""

    count = await attendance_service.get_pending_count(db)
    return {"count": count}
