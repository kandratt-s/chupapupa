"""Auth service schemas for API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user creation."""

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "SecurePass123",
                "first_name": "John",
                "last_name": "Doe",
            }
        }
    )


class UserUpdate(BaseModel):
    """Schema for user updates."""

    email: EmailStr | None = None
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    is_active: bool | None = None

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "newemail@example.com", "first_name": "Johnny"}}
    )


class UserResponse(BaseModel):
    """Schema for user response."""

    id: int
    username: str
    email: str
    first_name: str | None
    last_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    """Schema for role creation."""

    name: str = Field(..., min_length=3, max_length=100)
    description: str | None = Field(None, max_length=255)


class RoleResponse(BaseModel):
    """Schema for role response."""

    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
