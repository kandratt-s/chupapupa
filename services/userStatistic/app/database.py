"""
Модуль для настройки подключения к базе данных.
Создает соединение с PostgreSQL и предоставляет сессии для работы с БД.
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Создание движка базы данных
# echo=True включает логирование SQL запросов в режиме разработки
engine: Engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.LOG_LEVEL == "DEBUG",
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_recycle=3600,  # Переподключение каждый час
)

# Фабрика сессий для работы с БД
SessionLocal: sessionmaker[Session] = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency для получения сессии базы данных.

    Используется в FastAPI dependency injection.
    Автоматически закрывает сессию после завершения запроса.

    Yields:
        Session: Сессия SQLAlchemy для работы с БД
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Инициализация базы данных.

    Создает все таблицы, определенные в моделях.
    Вызывается при старте приложения.
    """
    from app.models import Base

    Base.metadata.create_all(bind=engine)
