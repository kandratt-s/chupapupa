"""Admin service schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminUserCreate(BaseModel):
    """Schema for admin user creation."""

    user_id: int
    role: str = Field(..., max_length=100)
    permissions: str | None = None
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    """Schema for admin user updates."""

    role: str | None = Field(None, max_length=100)
    permissions: str | None = None
    is_active: bool | None = None


class AdminUserResponse(BaseModel):
    """Schema for admin user response."""

    id: int
    user_id: int
    role: str
    permissions: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogCreate(BaseModel):
    """Schema for audit log creation."""

    admin_id: int
    action: str = Field(..., max_length=255)
    resource_type: str = Field(..., max_length=100)
    resource_id: int
    changes: str | None = None


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""

    id: int
    admin_id: int
    action: str
    resource_type: str
    resource_id: int
    changes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
