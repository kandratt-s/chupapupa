from fastapi import Depends, FastAPI, HTTPException, status
from models import AdminUser, AuditLog
from repositories import AdminUserRepository, AuditLogRepository
from schemas import (
    AdminUserCreate,
    AdminUserResponse,
    AdminUserUpdate,
    AuditLogCreate,
    AuditLogResponse,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db

app = FastAPI(
    title="Admin Service",
    description="Administrative operations and audit logging service",
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


# ==================== Admin User Endpoints ====================
@app.post(
    "/admin-users",
    response_model=AdminUserResponse,
    tags=["admin-users"],
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_user(
    admin_data: AdminUserCreate, db: AsyncSession = Depends(get_db)
) -> AdminUserResponse:
    """Create a new admin user."""
    repo = AdminUserRepository(db, AdminUser)

    # Check if user already is admin
    existing = await repo.get_by_user_id(admin_data.user_id)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already an admin")

    admin_user = await repo.create(
        user_id=admin_data.user_id,
        role=admin_data.role,
        permissions=admin_data.permissions,
        is_active=admin_data.is_active,
    )

    await repo.commit()
    return admin_user


@app.get("/admin-users", response_model=list[AdminUserResponse], tags=["admin-users"])
async def get_admin_users(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[AdminUser]:
    """Get all admin users with pagination."""
    repo = AdminUserRepository(db, AdminUser)
    users: list[AdminUser] = await repo.get_all(skip=skip, limit=limit)
    return users


@app.get("/admin-users/active", response_model=list[AdminUserResponse], tags=["admin-users"])
async def get_active_admin_users(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[AdminUser]:
    """Get all active admin users."""
    repo = AdminUserRepository(db, AdminUser)
    users: list[AdminUser] = await repo.get_active_admins(skip=skip, limit=limit)
    return users


@app.get("/admin-users/{admin_id}", response_model=AdminUserResponse, tags=["admin-users"])
async def get_admin_user(admin_id: int, db: AsyncSession = Depends(get_db)) -> AdminUserResponse:
    """Get admin user by ID."""
    repo = AdminUserRepository(db, AdminUser)
    user = await repo.get_by_id(admin_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")

    return user


@app.put("/admin-users/{admin_id}", response_model=AdminUserResponse, tags=["admin-users"])
async def update_admin_user(
    admin_id: int, admin_data: AdminUserUpdate, db: AsyncSession = Depends(get_db)
) -> AdminUserResponse:
    """Update admin user."""
    repo = AdminUserRepository(db, AdminUser)

    user = await repo.get_by_id(admin_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")

    update_data = admin_data.model_dump(exclude_unset=True)
    updated_user = await repo.update(admin_id, **update_data)

    await repo.commit()
    return updated_user


@app.delete("/admin-users/{admin_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["admin-users"])
async def delete_admin_user(admin_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete admin user."""
    repo = AdminUserRepository(db, AdminUser)

    deleted = await repo.delete(admin_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")

    await repo.commit()


@app.get(
    "/admin-users/by-user-id/{user_id}", response_model=AdminUserResponse, tags=["admin-users"]
)
async def get_admin_by_user_id(
    user_id: int, db: AsyncSession = Depends(get_db)
) -> AdminUserResponse:
    """Get admin user by user ID."""
    repo = AdminUserRepository(db, AdminUser)
    user = await repo.get_by_user_id(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")

    return user


# ==================== Audit Log Endpoints ====================
@app.post(
    "/audit-logs",
    response_model=AuditLogResponse,
    tags=["audit-logs"],
    status_code=status.HTTP_201_CREATED,
)
async def create_audit_log(
    log_data: AuditLogCreate, db: AsyncSession = Depends(get_db)
) -> AuditLogResponse:
    """Create a new audit log entry."""
    repo = AuditLogRepository(db, AuditLog)

    log = await repo.create(
        admin_id=log_data.admin_id,
        action=log_data.action,
        resource_type=log_data.resource_type,
        resource_id=log_data.resource_id,
        changes=log_data.changes,
    )

    await repo.commit()
    return log


@app.get("/audit-logs", response_model=list[AuditLogResponse], tags=["audit-logs"])
async def get_audit_logs(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[AuditLog]:
    """Get all audit logs with pagination."""
    repo = AuditLogRepository(db, AuditLog)
    logs: list[AuditLog] = await repo.get_all(skip=skip, limit=limit)
    return logs


@app.get("/audit-logs/{log_id}", response_model=AuditLogResponse, tags=["audit-logs"])
async def get_audit_log(log_id: int, db: AsyncSession = Depends(get_db)) -> AuditLogResponse:
    """Get audit log by ID."""
    repo = AuditLogRepository(db, AuditLog)
    log = await repo.get_by_id(log_id)

    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log not found")

    return log


@app.get("/audit-logs/admin/{admin_id}", response_model=list[AuditLogResponse], tags=["audit-logs"])
async def get_admin_logs(
    admin_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> list[AuditLog]:
    """Get audit logs for a specific admin."""
    repo = AuditLogRepository(db, AuditLog)
    logs: list[AuditLog] = await repo.get_logs_by_admin(admin_id, skip=skip, limit=limit)
    return logs


@app.get(
    "/audit-logs/resource/{resource_type}/{resource_id}",
    response_model=list[AuditLogResponse],
    tags=["audit-logs"],
)
async def get_resource_logs(
    resource_type: str,
    resource_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[AuditLog]:
    """Get audit logs for a specific resource."""
    repo = AuditLogRepository(db, AuditLog)
    logs: list[AuditLog] = await repo.get_logs_by_resource(
        resource_type, resource_id, skip=skip, limit=limit
    )
    return logs
