# Руководство по разработке CHUPAPUPA

## Структура кода

### Общие модули (shared/)

Содержит переиспользуемый код для всех сервисов:

- **base_model.py** - Базовая SQLAlchemy модель со стандартными полями (id, created_at, updated_at)
- **config.py** - Конфигурация приложения и БД через Pydantic Settings
- **database.py** - Менеджер для работы с БД и сессиями
- **repository.py** - Базовый CRUD репозиторий (Generic класс)
- **schemas.py** - Базовые Pydantic схемы

### Структура сервиса

Каждый сервис должен содержать:

```
service/
├── __init__.py
├── main.py          # FastAPI приложение с эндпоинтами
├── models.py        # SQLAlchemy модели
├── schemas.py       # Pydantic DTO схемы
├── repositories.py  # Логика работы с БД
├── db.py            # Конфигурация БД
├── Dockerfile       # Docker образ
├── requirements.txt # Зависимости
├── .env             # Переменные окружения
└── alembic/         # Миграции БД
    ├── env.py
    ├── versions/
    └── alembic.ini
```

## Разработка нового сервиса

### 1. Создание моделей

```python
# models.py
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from shared.base_model import BaseModel

class MyEntity(BaseModel):
    """Описание модели."""

    __tablename__ = "my_entities"
    __table_args__ = {"schema": "my_service"}

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
```

### 2. Создание схем

```python
# schemas.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class MyEntityCreate(BaseModel):
    """Для создания."""
    name: str = Field(..., min_length=1, max_length=255)

class MyEntityResponse(BaseModel):
    """Для ответа."""
    id: int
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 3. Создание репозитория

```python
# repositories.py
from sqlalchemy import select
from shared.repository import BaseRepository

class MyEntityRepository(BaseRepository[MyEntity]):
    """Специфичная логика для MyEntity."""

    async def find_by_name(self, name: str) -> Optional[MyEntity]:
        query = select(MyEntity).where(MyEntity.name == name)
        result = await self.session.execute(query)
        return result.scalars().first()
```

### 4. Создание эндпоинтов

```python
# main.py
from fastapi import Depends, HTTPException, status

@app.post("/my-entities", response_model=MyEntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(
    data: MyEntityCreate,
    db: AsyncSession = Depends(get_db)
) -> MyEntityResponse:
    """Создание сущности."""
    repo = MyEntityRepository(db, MyEntity)

    # Проверка
    existing = await repo.find_by_name(data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Entity already exists"
        )

    # Создание
    entity = await repo.create(name=data.name)
    await repo.commit()
    return entity

@app.get("/my-entities/{entity_id}", response_model=MyEntityResponse)
async def get_entity(
    entity_id: int,
    db: AsyncSession = Depends(get_db)
) -> MyEntityResponse:
    """Получение сущности."""
    repo = MyEntityRepository(db, MyEntity)
    entity = await repo.get_by_id(entity_id)

    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found"
        )

    return entity
```

## Работа с миграциями

### Автоматическое создание миграции

```bash
cd services/my_service
alembic revision --autogenerate -m "Add new fields to MyEntity"
```

### Ручное создание миграции

```bash
alembic revision -m "Custom migration"
# Отредактируйте созданный файл в versions/
```

### Применение миграций

```bash
# Применить все новые миграции
alembic upgrade head

# Применить N миграций
alembic upgrade +2

# Откатить до версии
alembic downgrade <revision>

# Посмотреть статус
alembic current
alembic history
```

## Асинхронность

Все операции с БД должны быть асинхронными:

```python
# Правильно
async def get_data():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(MyModel))
        return result.scalars().first()

# Неправильно
def get_data():
    session = AsyncSessionLocal()  # Ошибка: нужно async with
    result = session.execute(select(MyModel))  # Ошибка: нужно await
```

## Обработка ошибок

```python
from fastapi import HTTPException, status

# Правильная обработка ошибок
try:
    entity = await repo.get_by_id(id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found"
        )

    await repo.delete(id)
    await repo.commit()

except Exception as e:
    await repo.rollback()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error"
    )
```

## Dependency Injection

FastAPI использует встроенную систему DI через функции-параметры:

```python
# Получить сессию БД
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Использовать в маршруте
@app.get("/data")
async def get_data(db: AsyncSession = Depends(get_db)):
    # db готов к использованию
    pass

# Создать собственную зависимость
async def get_current_user(token: str = Header(...)):
    # валидация токена
    return user

@app.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    pass
```

## Валидация данных

```python
from pydantic import BaseModel, Field, validator

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: int = Field(..., ge=18, le=120)

    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('must be alphanumeric')
        return v
```

## Документирование API

```python
@app.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["users"],
    summary="Create a new user",
    description="Creates a new user and returns the created user with ID"
)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Create a new user.

    - **username**: Unique username (3-100 characters)
    - **email**: Valid email address
    - **password**: Secure password

    Returns the created user with generated ID.
    """
    # реализация
```

## Тестирование

### Структура тестов

```
tests/
├── conftest.py              # Общие фикстуры
├── test_auth.py
├── test_events.py
└── fixtures/
    └── sample_data.py
```

### Пример теста

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_user():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "SecurePass123"
            }
        )
        assert response.status_code == 201
        assert response.json()["username"] == "testuser"
```

## Логирование

```python
import logging

logger = logging.getLogger(__name__)

@app.post("/users")
async def create_user(data: UserCreate):
    logger.info(f"Creating user: {data.username}")

    try:
        user = await repo.create(**data.dict())
        logger.info(f"User created: {user.id}")
        return user
    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}")
        raise
```

## Best Practices

### 1. Используйте type hints

```python
# Хорошо
async def get_users(skip: int = 0, limit: int = 100) -> List[UserResponse]:
    pass

# Плохо
async def get_users(skip, limit):
    pass
```

### 2. Используйте docstrings

```python
def calculate_average(values: List[float]) -> float:
    """
    Calculate the average of the given values.

    Args:
        values: List of numeric values

    Returns:
        The average value

    Raises:
        ValueError: If values list is empty
    """
    pass
```

### 3. Управляйте ресурсами правильно

```python
# Используйте async context managers
async with AsyncSessionLocal() as session:
    # сессия автоматически закроется
    result = await session.execute(query)

# Не оставляйте открытые соединения
```

### 4. Кэширование

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_config():
    return load_config()

# Для асинхронного кэша можно использовать декораторы или redis
```

### 5. Константы

```python
# config.py
class Constants:
    MAX_USERNAME_LENGTH = 100
    MIN_PASSWORD_LENGTH = 8
    DEFAULT_ITEMS_PER_PAGE = 20

    class Roles:
        ADMIN = "admin"
        USER = "user"
        MODERATOR = "moderator"
```

## CI/CD

Рекомендуемые инструменты:

- **Linting**: ruff, pylint
- **Type checking**: mypy
- **Testing**: pytest, pytest-asyncio
- **Formatting**: black, ruff format

```bash
# Проверить стиль
ruff check .

# Проверить типы
mypy services/

# Запустить тесты
pytest -v --cov
```

## Мониторинг

Рекомендуется использовать:

- **Логирование**: Python logging, ELK Stack
- **Метрики**: Prometheus, StatsD
- **Трейсинг**: Jaeger, DataDog
- **Алерты**: Alertmanager

```python
from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    request_count.inc()
    # ... логирование времени выполнения
```

## Развертывание

### Docker

```bash
# Собрать образ
docker build -f services/auth/Dockerfile -t auth-service:1.0 .

# Запустить контейнер
docker run -p 8001:8000 auth-service:1.0

# Используя Docker Compose
docker-compose up -d
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: auth-service
  template:
    metadata:
      labels:
        app: auth-service
    spec:
      containers:
      - name: auth-service
        image: auth-service:1.0
        ports:
        - containerPort: 8000
        env:
        - name: DB_HOST
          value: postgres
        - name: DB_USER
          value: auth_user
```

## Безопасность

### HTTPS/TLS

```python
# Используйте HTTPS в production
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["example.com", "*.example.com"]
)
```

### CORS

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limiting

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginSchema):
    # ограничение 5 попыток в минуту
    pass
```

---

Для вопросов и дополнений, пожалуйста, обновите этот документ или создайте Issue.
