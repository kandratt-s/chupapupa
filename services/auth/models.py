"""Auth service models."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from shared.base_model import BaseModel


class User(BaseModel):
    """User model for authentication."""

    __tablename__ = "users"
    __table_args__ = {"schema": "auth_service"}

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<User id={self.id} username={self.username}>"


class Role(BaseModel):
    """Role model for access control."""

    __tablename__ = "roles"
    __table_args__ = {"schema": "auth_service"}

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Role id={self.id} name={self.name}>"
