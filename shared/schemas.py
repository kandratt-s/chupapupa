"""Base Pydantic schemas for API requests/responses."""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class TimestampMixin(BaseModel):
    """Mixin for models with timestamps."""

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BaseSchema(BaseModel):
    """Base schema with ID."""

    id: int

    model_config = ConfigDict(from_attributes=True)


class BaseSchemaWithTimestamp(BaseSchema, TimestampMixin):
    """Base schema with ID and timestamps."""

    pass


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str
    error_code: str | None = None
