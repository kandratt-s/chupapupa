# CHUPAPUPA
## Микросервисная архитектура для управления событиями

CHUPAPUPA - это современная микросервисная система для управления событиями, учета посещаемости и администрирования, построенная на основе FastAPI и PostgreSQL.

## Архитектура проекта

### Сервисы

1. **Auth Service** (Port 8001) - Аутентификация и управление пользователями
   - Управление пользователями
   - Управление ролями
   - Аутентификация и авторизация

2. **Event Service** (Port 8006) - Управление событиями
   - Создание и управление событиями
   - Управление участниками события
   - Регистрация на события

3. **Attendance Service** (Port 8003) - Учет посещаемости
   - Регистрация посещаемости
   - История посещений
   - Отчеты по посещаемости

4. **Admin Service** (Port 8002) - Административные функции
   - Управление администраторами
   - Логирование аудита
   - Отслеживание изменений

5. **CV Service** (Port 8005) - Управление резюме
   - Хранение резюме пользователей
   - Публичные и приватные резюме
   - Управление профилями

6. **User Statistic Service** (Port 8007) - Статистика пользователей
   - Статистика участия
   - Рейтинги пользователей
   - Аналитика активности

7. **Bot Service** (Port 8004) - Сервис ботов
   - Интеграции с ботами
   - Автоматизация операций

8. **Web Service** (Port 8008) - Веб-сервис
   - Интеграция фронтенда
   - Дополнительные веб-функции

### База данных

- **PostgreSQL** - Single instance с отдельными схемами для каждого сервиса
- **Alembic** - Управление миграциями БД
- **SQLAlchemy** - ORM для работы с БД

## Требования

- Python 3.11+
- PostgreSQL 13+
- Docker & Docker Compose
- pip

## Установка и запуск

### Используя Docker Compose

```bash
# Скачайте проект
git clone <repo-url>
cd chupapupa

# Создайте файлы .env для каждого сервиса
# Пример для services/auth/.env:
APP_SERVICE_NAME=auth
APP_SERVICE_PORT=8000
APP_DEBUG=true
DB_USER=auth_user
DB_PASSWORD=auth_pass

# Запустите контейнеры
docker-compose up -d

# Проверьте статус
docker-compose ps
```

### Локальная разработка

```bash
# Установите зависимости для каждого сервиса
pip install -r requirements-base.txt

# Для каждого сервиса:
cd services/auth
pip install -r requirements.txt

# Запустите миграции Alembic
alembic upgrade head

# Запустите сервис
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

## Структура проекта

```
chupapupa/
├── shared/                  # Общие модули
│   ├── base_model.py       # Базовая модель SQLAlchemy
│   ├── config.py           # Конфигурация
│   ├── database.py         # Управление БД
│   ├── repository.py       # Базовый репозиторий
│   └── schemas.py          # Базовые схемы Pydantic
├── services/               # Микросервисы
│   ├── auth/              # Сервис аутентификации
│   ├── event/             # Сервис событий
│   ├── attendance/        # Сервис посещаемости
│   ├── admin/             # Административный сервис
│   ├── CV/                # Сервис резюме
│   ├── userStatistic/     # Сервис статистики
│   ├── bot/               # Сервис ботов
│   ├── web/               # Веб-сервис
│   └── Gateway/           # API Gateway
├── db/                     # Скрипты БД
│   └── init-scripts/       # SQL-скрипты инициализации
└── docker-compose.yml      # Docker Compose конфиг
```

## API Endpoints

### Auth Service (http://localhost:8001)

```
POST   /users                      - Создать пользователя
GET    /users                      - Получить всех пользователей
GET    /users/{user_id}            - Получить пользователя
PUT    /users/{user_id}            - Обновить пользователя
DELETE /users/{user_id}            - Удалить пользователя
GET    /users/search/by-username/{username} - Найти по имени
GET    /health                     - Проверка здоровья сервиса

POST   /roles                      - Создать роль
GET    /roles                      - Получить все роли
GET    /roles/{role_id}            - Получить роль
PUT    /roles/{role_id}            - Обновить роль
DELETE /roles/{role_id}            - Удалить роль
```

### Event Service (http://localhost:8006)

```
POST   /events                     - Создать событие
GET    /events                     - Получить все события
GET    /events/{event_id}          - Получить событие
PUT    /events/{event_id}          - Обновить событие
DELETE /events/{event_id}          - Удалить событие
GET    /events/organizer/{organizer_id} - События организатора

POST   /attendees                  - Зарегистрировать участника
GET    /events/{event_id}/attendees - Получить участников события
GET    /users/{user_id}/events     - События пользователя
DELETE /attendees/{attendee_id}    - Отменить регистрацию
```

### Attendance Service (http://localhost:8003)

```
POST   /attendance                 - Создать запись посещаемости
GET    /attendance                 - Получить все записи
GET    /attendance/{attendance_id} - Получить запись
PUT    /attendance/{attendance_id} - Обновить запись
DELETE /attendance/{attendance_id} - Удалить запись
GET    /users/{user_id}/attendance - Посещаемость пользователя
GET    /events/{event_id}/attendance - Посещаемость события
```

### Admin Service (http://localhost:8002)

```
POST   /admin-users                - Создать администратора
GET    /admin-users                - Получить администраторов
GET    /admin-users/{admin_id}     - Получить администратора
PUT    /admin-users/{admin_id}     - Обновить администратора
DELETE /admin-users/{admin_id}     - Удалить администратора

POST   /audit-logs                 - Создать запись аудита
GET    /audit-logs                 - Получить логи аудита
GET    /audit-logs/admin/{admin_id} - Логи администратора
GET    /audit-logs/resource/{type}/{id} - Логи ресурса
```

### CV Service (http://localhost:8005)

```
POST   /cvs                        - Создать резюме
GET    /cvs                        - Получить все резюме
GET    /cvs/{cv_id}                - Получить резюме
PUT    /cvs/{cv_id}                - Обновить резюме
DELETE /cvs/{cv_id}                - Удалить резюме
GET    /cvs/public                 - Получить публичные резюме
GET    /cvs/user/{user_id}         - Резюме пользователя
```

### User Statistic Service (http://localhost:8007)

```
POST   /statistics                 - Создать статистику
GET    /statistics                 - Получить статистику
GET    /statistics/{stat_id}       - Получить статистику
PUT    /statistics/{stat_id}       - Обновить статистику
DELETE /statistics/{stat_id}       - Удалить статистику
GET    /statistics/user/{user_id}  - Статистика пользователя
GET    /statistics/top-users       - Топ пользователей
```

## Работа с миграциями

```bash
# Создать новую миграцию
cd services/auth
alembic revision --autogenerate -m "Описание изменения"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Просмотреть историю миграций
alembic history
```

## Переменные окружения

Каждый сервис требует файла `.env` со следующими переменными:

```env
# Application
APP_SERVICE_NAME=auth
APP_SERVICE_PORT=8000
APP_DEBUG=false
APP_LOG_LEVEL=INFO

# Database
DB_HOST=postgres
DB_PORT=5432
DB_USER=auth_user
DB_PASSWORD=auth_pass
DB_DATABASE=chupapupa
DB_SCHEMA=auth_service
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_ECHO=false
```

## Разработка

### Создание нового сервиса

1. Создайте директорию в `services/`
2. Создайте структуру:
   - `main.py` - FastAPI приложение
   - `models.py` - SQLAlchemy модели
   - `schemas.py` - Pydantic схемы
   - `repositories.py` - CRUD операции
   - `db.py` - Конфигурация БД
   - `requirements.txt` - Зависимости
   - `Dockerfile` - Образ контейнера
   - `alembic/` - Миграции

3. Скопируйте `alembic/` из существующего сервиса
4. Создайте `.env` файл

### Тестирование

```bash
# Запустить тесты (если есть)
pytest

# Проверить стиль кода
ruff check .

# Проверить типы
mypy .
```

## API документация

После запуска сервиса, документация доступна по адресам:

- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

## Проблемы и решения

### Проблема с подключением к БД

Убедитесь, что PostgreSQL запущен и доступен:

```bash
# Проверьте статус контейнера
docker-compose ps postgres

# Посмотрите логи
docker-compose logs postgres
```

### Проблема с миграциями

```bash
# Убедитесь, что правильно установлена схема в env.py
# Проверьте alembic.ini

# Попробуйте запустить в offline режиме
alembic upgrade head --sql
```

## Лицензия

Укажите лицензию вашего проекта здесь.

## Контакты

Для вопросов и поддержки обратитесь к команде разработки.
