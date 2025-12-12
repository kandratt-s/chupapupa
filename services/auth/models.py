from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    hse_email = Column(String(100), unique=True, index=True, nullable=False)
    telegram_id = Column(String(50), unique=True, nullable=True)
    role = Column(String(20), default="student")
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200))
    student_id = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    profile_photo = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, nullable=True)