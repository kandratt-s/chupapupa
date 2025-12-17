# CHUPAPUPA Microservices - Unified Deployment Guide

## 🚀 Быстрый запуск

```bash
# Клонировать репозиторий
git clone <repository-url>
cd chupapupa

# Создать .env файл из примера
cp .env.example .env

# Запустить всю систему одной командой
docker-compose up --build
```

## 📋 Архитектура системы

### Внешний доступ
- **API Gateway**: `http://localhost:8000` - единственная точка входа
- **Документация**: `http://localhost:8000/docs`
- **Мониторинг**: `http://localhost:8000/health`

### Внутренние сервисы (изолированы)
- **PostgreSQL**: `postgres:5432` (внутренняя сеть)
- **Auth Service**: `auth-service:8000`
- **Event Service**: `event-service:8000`
- **Attendance Service**: `attendance-service:8003`
- **User Statistics**: `user-statistic-service:8000`
- **Admin Service**: `admin-service:8000`
- **Bot Service**: `bot-service:8000`
- **Web Service**: `web-service:8000`

## 📁 Структура хранения фотографий

```
/shared/photos/
├── faces/                    # userStatistic service
│   ├── raw/                 # исходные фотографии лиц
│   ├── processed/           # обработанные фотографии
│   └── thumbnails/          # миниатюры
└── attendances/             # attendance service  
    ├── uploads/             # загруженные файлы
    ├── verified/            # проверенные файлы
    └── thumbnails/          # миниатюры
```

## 🛠 Команды управления

### Запуск системы
```bash
# Запуск в фоновом режиме
docker-compose up -d

# Просмотр логов всех сервисов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f api-gateway
docker-compose logs -f attendance-service
```

### Мониторинг
```bash
# Статус всех контейнеров
docker-compose ps

# Проверка здоровья системы
curl http://localhost:8000/health

# Статистика API Gateway
curl http://localhost:8000/stats
```

### Остановка и очистка
```bash
# Остановить все сервисы
docker-compose down

# Удалить все данные (включая базу)
docker-compose down -v

# Полная очистка (включая образы)
docker-compose down -v --rmi all
```

## 🔗 API Endpoints

### Через API Gateway (http://localhost:8000)

#### Authentication
- `POST /auth/login` - вход в систему
- `POST /auth/register` - регистрация
- `GET /auth/verify-token` - проверка токена

#### Events
- `GET /events/` - список мероприятий
- `POST /events/` - создание мероприятия

#### Attendance
- `GET /attendance/` - список посещений
- `POST /attendance/upload` - загрузка файла посещения

#### User Statistics
- `GET /user-statistics/` - статистика пользователей

#### Admin
- `GET /admin/` - административные функции

### Gateway Management
- `GET /` - информация о системе
- `GET /health` - состояние всех сервисов
- `GET /stats` - статистика запросов
- `GET /routes` - доступные маршруты
- `GET /docs` - Swagger документация

## ⚙️ Переменные окружения

Основные переменные в `.env`:

```bash
# Общие настройки
ENVIRONMENT=development
DEBUG=true

# База данных
POSTGRES_DB=chupapupa_pj
POSTGRES_USER=postgres  
POSTGRES_PASSWORD=postgresZXC

# API Gateway
GATEWAY_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key-here-change-in-production

# File uploads
MAX_FILE_SIZE=10485760  # 10MB
PHOTOS_BASE_PATH=/shared/photos
```

## 🔧 Разработка

### Локальная разработка сервиса
```bash
# Запуск только базы данных
docker-compose up postgres -d

# Разработка attendance service локально
cd services/attendance
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn main:app --reload --port 8003
```

### Добавление нового сервиса

1. Создать папку в `services/`
2. Добавить Dockerfile
3. Обновить `docker-compose.yml`
4. Добавить маршрут в API Gateway
5. Обновить health checks

### Отладка
```bash
# Подключение к контейнеру
docker-compose exec api-gateway sh
docker-compose exec postgres psql -U postgres -d chupapupa_pj

# Просмотр сети Docker
docker network ls
docker network inspect chupapupa_internal-network
```

## 🔒 Безопасность

- **Изоляция сервисов**: только API Gateway доступен извне
- **Аутентификация**: JWT токены через auth service
- **CORS**: настраивается в API Gateway
- **Файлы**: валидация типов и размеров
- **Логирование**: все запросы логируются

## 📊 Мониторинг

### Health Checks
- API Gateway: автоматическая проверка всех сервисов
- База данных: проверка подключения
- Каждый сервис: собственный `/health` endpoint

### Логирование
- Все запросы логируются с временными метками
- Цветовая индикация статусов (🟢 успех, 🔴 ошибка)
- Статистика производительности

### Метрики
- Общее количество запросов
- Успешные/неуспешные запросы  
- Среднее время ответа
- Доступность сервисов

## 🚨 Troubleshooting

### Частые проблемы

1. **Порт 8000 занят**
   ```bash
   # Изменить порт в .env
   GATEWAY_PORT=8080
   ```

2. **База данных не запускается**
   ```bash
   # Очистить данные и перезапустить
   docker-compose down -v
   docker-compose up postgres -d
   ```

3. **Сервис недоступен**
   ```bash
   # Проверить логи
   docker-compose logs service-name
   
   # Перезапустить сервис
   docker-compose restart service-name
   ```

4. **Ошибки аутентификации**
   ```bash
   # Проверить auth service
   curl http://localhost:8000/auth/health
   ```

### Полезные команды
```bash
# Проверка всех контейнеров
docker ps

# Очистка неиспользуемых образов
docker system prune -f

# Мониторинг ресурсов
docker stats

# Бэкап базы данных
docker-compose exec postgres pg_dump -U postgres chupapupa_pj > backup.sql
```

## 📈 Production Deploy

### Изменения для продакшена

1. **Переменные окружения**:
   - Изменить `JWT_SECRET_KEY`
   - Установить `ENVIRONMENT=production`
   - Настроить `CORS_ORIGINS`

2. **База данных**:
   - Использовать внешний PostgreSQL
   - Настроить резервное копирование

3. **Безопасность**:
   - HTTPS через reverse proxy (nginx)
   - Ограничить ресурсы контейнеров
   - Настроить мониторинг

4. **Масштабирование**:
   - Добавить load balancer
   - Использовать docker swarm или kubernetes