"""Admin service models."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.base_model import BaseModel


class AdminUser(BaseModel):
    """Admin user model."""

    __tablename__ = "admin_users"
    __table_args__ = {"schema": "admin_service"}

    user_id: Mapped[int] = mapped_column(nullable=False, unique=True, index=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    permissions: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<AdminUser id={self.id} user_id={self.user_id} role={self.role}>"


class AuditLog(BaseModel):
    """Audit log model."""

    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "admin_service"}

    admin_id: Mapped[int] = mapped_column(nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[int] = mapped_column(nullable=False)
    changes: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<AuditLog id={self.id} action={self.action}>"
