from fastapi import Depends, FastAPI, HTTPException, status
from models import UserStatistic
from repositories import UserStatisticRepository
from schemas import UserStatisticCreate, UserStatisticResponse, UserStatisticUpdate
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db

app = FastAPI(
    title="User Statistic Service",
    description="User statistics and analytics service",
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
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection failed"
        ) from err


# ==================== User Statistic Endpoints ====================
@app.post(
    "/statistics",
    response_model=UserStatisticResponse,
    tags=["statistics"],
    status_code=status.HTTP_201_CREATED,
)
async def create_statistic(
    stat_data: UserStatisticCreate, db: AsyncSession = Depends(get_db)
) -> UserStatisticResponse:
    """Create a new user statistic record."""
    repo = UserStatisticRepository(db, UserStatistic)

    # Check if user already has statistics
    existing = await repo.get_by_user_id(stat_data.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User statistics already exist"
        )

    statistic = await repo.create(
        user_id=stat_data.user_id,
        events_attended=stat_data.events_attended,
        events_organized=stat_data.events_organized,
        total_hours=stat_data.total_hours,
        average_rating=stat_data.average_rating,
        last_activity=stat_data.last_activity,
    )

    await repo.commit()
    return statistic


@app.get("/statistics", response_model=list[UserStatisticResponse], tags=["statistics"])
async def get_all_statistics(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[UserStatistic]:
    """Get all user statistics with pagination."""
    repo = UserStatisticRepository(db, UserStatistic)
    statistics: list[UserStatistic] = await repo.get_all(skip=skip, limit=limit)
    return statistics


@app.get("/statistics/top-users", response_model=list[UserStatisticResponse], tags=["statistics"])
async def get_top_users(limit: int = 10, db: AsyncSession = Depends(get_db)) -> list[UserStatistic]:
    """Get top users by average rating."""
    repo = UserStatisticRepository(db, UserStatistic)
    users: list[UserStatistic] = await repo.get_top_users(limit=limit)
    return users


@app.get("/statistics/{stat_id}", response_model=UserStatisticResponse, tags=["statistics"])
async def get_statistic(stat_id: int, db: AsyncSession = Depends(get_db)) -> UserStatisticResponse:
    """Get user statistic by ID."""
    repo = UserStatisticRepository(db, UserStatistic)
    statistic = await repo.get_by_id(stat_id)

    if not statistic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User statistic not found"
        )

    return statistic


@app.put("/statistics/{stat_id}", response_model=UserStatisticResponse, tags=["statistics"])
async def update_statistic(
    stat_id: int, stat_data: UserStatisticUpdate, db: AsyncSession = Depends(get_db)
) -> UserStatisticResponse:
    """Update user statistic."""
    repo = UserStatisticRepository(db, UserStatistic)

    statistic = await repo.get_by_id(stat_id)
    if not statistic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User statistic not found"
        )

    update_data = stat_data.model_dump(exclude_unset=True)
    updated_statistic = await repo.update(stat_id, **update_data)

    await repo.commit()
    return updated_statistic


@app.delete("/statistics/{stat_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["statistics"])
async def delete_statistic(stat_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete user statistic."""
    repo = UserStatisticRepository(db, UserStatistic)

    deleted = await repo.delete(stat_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User statistic not found"
        )

    await repo.commit()


@app.get("/statistics/user/{user_id}", response_model=UserStatisticResponse, tags=["statistics"])
async def get_user_statistic(
    user_id: int, db: AsyncSession = Depends(get_db)
) -> UserStatisticResponse:
    """Get statistics for a specific user."""
    repo = UserStatisticRepository(db, UserStatistic)
    statistic = await repo.get_by_user_id(user_id)

    if not statistic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User statistic not found"
        )

    return statistic
