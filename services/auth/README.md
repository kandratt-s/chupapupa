# Auth Service

Микросервис аутентификации для системы управления событиями ВШЭ.

## Описание

Auth сервис обрабатывает только аутентификацию и авторизацию пользователей:
- Выдача JWT токенов (access + refresh)
- Проверка учетных данных
- Управление ролями пользователей
- Административные функции для управления аутентификацией

## Архитектура

### База данных
Использует схему `auth_service.auth`:
```sql
CREATE TABLE auth_service.auth (
    user_id INTEGER PRIMARY KEY,           -- ID из userStatistic сервиса
    password_hash VARCHAR(255) NOT NULL,   -- Хеш пароля (bcrypt)
    role VARCHAR(20) NOT NULL DEFAULT 'user', -- Роль: 'user' или 'admin'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES public.users(user_id)
);
```

### JWT токены
- **Access token**: Время жизни 30 минут
- **Refresh token**: Время жизни 7 дней
- Алгоритм: HS256
- Полезная нагрузка: `user_id`, `role`, `exp`, `type`

### Роль в микросервисной архитектуре
**Auth сервис = БАЗОВЫЙ СЕРВИС** - не требует авторизации для управления:
- Предоставляет JWT токены через `/login`
- Управляется Admin сервисом через открытые эндпоинты
- Другие сервисы получают роли через заголовки от Gateway

## API Endpoints

### Публичные
- `POST /login` - Авторизация пользователя (выдача JWT токенов)
- `POST /refresh` - Обновление токенов по refresh токену
- `GET /` - Health check
- `GET /health` - Детальный health check

### Пользовательские (требуют JWT токен)
- `PUT /change-password` - Смена пароля пользователем

### Сервисные (используются Admin сервисом)
- `POST /auth/create` - Создание записи аутентификации
- `PUT /auth/{user_id}` - Обновление записи аутентификации  
- `GET /auth/{user_id}` - Получение информации о роли пользователя

**ВАЖНО**: Сервисные эндпоинты НЕ требуют авторизации, так как Auth является базовым сервисом.

## Запуск в Docker

### 1. Подготовка PostgreSQL
```bash
# Поднимаем общую БД
cd ../../db
docker-compose -f docker-compose.postgres.yml up -d
```

### 2. Запуск сервиса
```bash
# Запускаем Auth сервис
docker-compose up
```

Сервис будет доступен по адресу: http://localhost:8001

### 3. Тестирование
```bash
# Запускаем тесты
chmod +x test_auth.sh
./test_auth.sh
```

## Переменные окружения

### Обязательные
- `SECRET_KEY` - **КРИТИЧЕСКИ ВАЖНО!** Секретный ключ для JWT (сгенерируйте безопасный)

### Необязательные
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Время жизни access токенов (по умолчанию: 15 мин)
- `REFRESH_TOKEN_EXPIRE_DAYS` - Время жизни refresh токенов (по умолчанию: 7 дней)
- `DATABASE_URL` - Строка подключения к PostgreSQL
- `DEBUG` - Режим отладки
- `ENVIRONMENT` - Среда выполнения

### Генерация SECRET_KEY
```bash
# Сгенерируйте безопасный ключ:
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Пример результата:
# k8vQ2xM5F9nP7gL3wR1eA6hJ4uY8sD0tZ9mN2bC6vX1Q
```

### Настройка для продакшена
```bash
# Обязательно установите в production:
export SECRET_KEY="your-generated-key-here"
export ACCESS_TOKEN_EXPIRE_MINUTES=15
export REFRESH_TOKEN_EXPIRE_DAYS=7
export ENVIRONMENT=production
export DEBUG=false
```

## Интеграция с другими сервисами

### userStatistic Service
- Auth сервис НЕ управляет пользователями
- `user_id` в Auth таблице ссылается на пользователей из userStatistic (Foreign Key)
- userStatistic отвечает за создание/управление профилями
- userStatistic получает роли через заголовки `X-User-ID`, `X-User-Role` от Gateway

### Admin Service  
- Admin сервис управляет Auth сервисом через открытые эндпоинты
- Самостоятельной регистрации НЕТ
- Admin создает записи аутентификации после создания пользователей

### Gateway/Reverse Proxy
- Проверяет JWT токены от Auth сервиса
- Добавляет заголовки `X-User-ID`, `X-User-Role` в запросы к другим сервисам
- Другие сервисы получают информацию о пользователе через заголовки

### Workflow создания пользователя
1. **userStatistic** создает профиль пользователя → получает `user_id`
2. **Admin сервис** вызывает `POST /auth/create` (без авторизации)
3. Пользователь может входить через `POST /login`
4. **Gateway** проверяет JWT и добавляет заголовки для других сервисов

### Правильная архитектура
```
Auth (базовый) → выдает JWT токены
Gateway → проверяет JWT → добавляет заголовки X-User-*
userStatistic → читает заголовки → определяет роли
```

## Безопасность

- Пароли хешируются с помощью bcrypt
- JWT токены подписываются SECRET_KEY
- Валидация входных данных через Pydantic
- Разделение access/refresh токенов
- Роли для авторизации

## Структура проекта

```
auth/
├── main_auth.py         # FastAPI приложение
├── models.py           # SQLAlchemy модели
├── schemas.py          # Pydantic схемы
├── database.py         # Конфигурация БД
├── crud.py             # CRUD операции
├── auth.py             # JWT функции
├── requirements.txt    # Зависимости
├── Dockerfile          # Docker образ
├── docker-compose.yml  # Локальная разработка
└── test_auth.sh        # Тесты
```

## Разработка

### Локальный запуск (без Docker)
```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера
uvicorn main_auth:app --host 0.0.0.0 --port 8001 --reload
```

### Примеры запросов

#### Авторизация
```bash
curl -X POST "http://localhost:8001/login" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "password": "mypassword"}'
```

#### Обновление токена
```bash
curl -X POST "http://localhost:8001/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your_refresh_token_here"}'
```

#### Смена пароля пользователем
```bash
curl -X PUT "http://localhost:8001/change-password" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_access_token_here" \
  -d '{"current_password": "old_password", "new_password": "new_password"}'
```

#### Создание пользователя (Admin сервис)
```bash
curl -X POST "http://localhost:8001/auth/create" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "password": "password123", "role": "user"}'
```

#### Получение информации (для других сервисов)
```bash
curl -X GET "http://localhost:8001/auth/1"
```