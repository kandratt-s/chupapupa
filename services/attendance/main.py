from fastapi import Depends, FastAPI, HTTPException, status
from models import Attendance
from repositories import AttendanceRepository
from schemas import AttendanceCreate, AttendanceResponse, AttendanceUpdate
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db

app = FastAPI(
    title="Attendance Service",
    description="Attendance tracking and management service",
    version="1.0.0",
)


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


# ==================== Attendance Endpoints ====================
@app.post(
    "/attendance",
    response_model=AttendanceResponse,
    tags=["attendance"],
    status_code=status.HTTP_201_CREATED,
)
async def create_attendance(
    attendance_data: AttendanceCreate, db: AsyncSession = Depends(get_db)
) -> AttendanceResponse:
    """Create a new attendance record."""
    repo = AttendanceRepository(db, Attendance)

    record = await repo.create(
        user_id=attendance_data.user_id,
        event_id=attendance_data.event_id,
        photo_path=attendance_data.photo_path,
        is_approved=attendance_data.is_approved,
    )

    await repo.commit()
    return record


@app.get("/attendance", response_model=list[AttendanceResponse], tags=["attendance"])
async def get_all_attendance(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Attendance]:
    """Get all attendance records with pagination."""
    repo = AttendanceRepository(db, Attendance)
    records: list[Attendance] = await repo.get_all(skip=skip, limit=limit)
    return records


@app.get("/attendance/{attendance_id}", response_model=AttendanceResponse, tags=["attendance"])
async def get_attendance(
    attendance_id: int, db: AsyncSession = Depends(get_db)
) -> AttendanceResponse:
    """Get attendance record by ID."""
    repo = AttendanceRepository(db, Attendance)
    record = await repo.get_by_id(attendance_id)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found",
        )

    return record


@app.put("/attendance/{attendance_id}", response_model=AttendanceResponse, tags=["attendance"])
async def update_attendance(
    attendance_id: int, attendance_data: AttendanceUpdate, db: AsyncSession = Depends(get_db)
) -> AttendanceResponse:
    """Update attendance record."""
    repo = AttendanceRepository(db, Attendance)

    record = await repo.get_by_id(attendance_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found",
        )

    update_data = attendance_data.model_dump(exclude_unset=True)
    updated_record = await repo.update(attendance_id, **update_data)

    await repo.commit()
    return updated_record


@app.delete(
    "/attendance/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["attendance"]
)
async def delete_attendance(attendance_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete attendance record."""
    repo = AttendanceRepository(db, Attendance)

    deleted = await repo.delete(attendance_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found",
        )

    await repo.commit()


@app.get(
    "/users/{user_id}/attendance", response_model=list[AttendanceResponse], tags=["attendance"]
)
async def get_user_attendance(
    user_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Attendance]:
    """Get all attendance records for a specific user."""
    repo = AttendanceRepository(db, Attendance)
    records: list[Attendance] = await repo.get_user_attendance(user_id, skip=skip, limit=limit)
    return records


@app.get(
    "/events/{event_id}/attendance", response_model=list[AttendanceResponse], tags=["attendance"]
)
async def get_event_attendance(
    event_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[Attendance]:
    """Get all attendance records for a specific event."""
    repo = AttendanceRepository(db, Attendance)
    records: list[Attendance] = await repo.get_event_attendance(event_id, skip=skip, limit=limit)
    return records
