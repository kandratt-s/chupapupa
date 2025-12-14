"""
Сервис для управления записями посещаемости
"""

from datetime import datetime

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import APPROVED, PENDING, REJECTED, REVIEWING, AttendanceRecord
from src.models.schemas import AttendanceCreate, AttendanceReview
from src.services.photo_service import PhotoService


class AttendanceService:
    """Сервис для управления записями посещаемости"""

    def __init__(self, photo_service: PhotoService):
        self.photo_service = photo_service

    async def create_attendance(
        self, db: AsyncSession, user_id: int, data: AttendanceCreate, photo: UploadFile
    ) -> AttendanceRecord:
        """Создать новую заявку на посещаемость"""

        # Проверяем, нет ли уже активной заявки от этого пользователя на это мероприятие
        existing = await self._get_active_attendance_by_user_event(db, user_id, data.event_id)
        if existing:
            raise HTTPException(
                status_code=400, detail="У вас уже есть активная заявка на это мероприятие"
            )

        # Создаем новую запись
        attendance = AttendanceRecord(
            event_id=data.event_id,
            user_id=user_id,
            notes=data.notes,
            status=PENDING,
            created_at=datetime.utcnow(),
        )

        db.add(attendance)
        await db.flush()  # Получаем ID
        await db.refresh(attendance)

        # Сохраняем файл (фото или PDF)
        file_path = await self.photo_service.save_attendance_photo(photo, attendance.attendance_id)
        attendance.file_path = file_path

        await db.commit()
        return attendance

    async def get_user_attendances(
        self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 50
    ) -> tuple[list[AttendanceRecord], int]:
        """Получить список заявок пользователя"""

        query = (
            select(AttendanceRecord)
            .where(AttendanceRecord.user_id == user_id)
            .order_by(AttendanceRecord.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        attendances = result.scalars().all()

        # Подсчет общего количества
        count_query = select(func.count()).where(AttendanceRecord.user_id == user_id)
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return list(attendances), total or 0

    async def get_pending_attendances(
        self, db: AsyncSession, skip: int = 0, limit: int = 50
    ) -> tuple[list[AttendanceRecord], int]:
        """Получить список заявок на рассмотрение"""

        query = (
            select(AttendanceRecord)
            .where(AttendanceRecord.status == PENDING)
            .order_by(AttendanceRecord.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        attendances = result.scalars().all()

        count_query = select(func.count()).where(AttendanceRecord.status == PENDING)
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return list(attendances), total or 0

    async def get_attendance_by_id(
        self, db: AsyncSession, attendance_id: int
    ) -> AttendanceRecord | None:
        """Получить заявку по ID"""
        return await db.get(AttendanceRecord, attendance_id)

    async def start_review(
        self, db: AsyncSession, attendance_id: int, admin_id: int
    ) -> AttendanceRecord:
        """Начать рассмотрение заявки (заблокировать для других админов)"""

        attendance = await db.get(AttendanceRecord, attendance_id)
        if not attendance:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        if attendance.status != PENDING:
            raise HTTPException(status_code=400, detail="Заявка недоступна для рассмотрения")

        # Устанавливаем статус "на рассмотрении" и назначаем админа
        attendance.status = REVIEWING
        attendance.reviewed_by = admin_id

        await db.commit()
        await db.refresh(attendance)
        return attendance

    async def submit_review(
        self, db: AsyncSession, attendance_id: int, admin_id: int, review_data: AttendanceReview
    ) -> AttendanceRecord:
        """Завершить рассмотрение заявки"""

        attendance = await db.get(AttendanceRecord, attendance_id)
        if not attendance:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        # Проверяем статус заявки и блокируем если нужно
        if attendance.status == PENDING:
            # Автоматически блокируем заявку на текущего админа
            attendance.status = REVIEWING
            attendance.reviewed_by = admin_id
            await db.commit()
        elif attendance.status == REVIEWING and attendance.reviewed_by != admin_id:
            # Заявка уже заблокирована другим админом
            raise HTTPException(
                status_code=403, detail="Заявка находится на рассмотрении у другого администратора"
            )
        elif attendance.status not in [PENDING, REVIEWING]:
            raise HTTPException(status_code=400, detail="Заявка уже обработана")

        # Обновляем статус
        if review_data.approve:
            attendance.status = APPROVED
            attendance.is_aproved = True
        else:
            attendance.status = REJECTED

        attendance.notes = review_data.notes
        attendance.checked_at = datetime.utcnow()

        await db.commit()
        await db.refresh(attendance)
        return attendance

    async def get_pending_count(self, db: AsyncSession) -> int:
        """Получить количество заявок в ожидании"""
        query = select(func.count()).where(AttendanceRecord.status == PENDING)
        result = await db.execute(query)
        return result.scalar() or 0

    async def _get_active_attendance_by_user_event(
        self, db: AsyncSession, user_id: int, event_id: int
    ) -> AttendanceRecord | None:
        """Проверить есть ли активная заявка пользователя на мероприятие"""

        active_statuses = [PENDING, REVIEWING, APPROVED]

        query = select(AttendanceRecord).where(
            AttendanceRecord.user_id == user_id,
            AttendanceRecord.event_id == event_id,
            AttendanceRecord.status.in_(active_statuses),
        )
        result = await db.execute(query)
        return result.scalars().first()
