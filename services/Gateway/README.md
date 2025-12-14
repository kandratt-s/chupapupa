# CHUPAPUPA API Gateway v2.0

## 📋 Описание

API Gateway - это центральная точка доступа ко всем микросервисам системы CHUPAPUPA. Обеспечивает маршрутизацию запросов, аутентификацию, логирование и мониторинг.

## 🏗️ Архитектура

```
Gateway/
├── main.py                 # Главный файл FastAPI приложения
├── app/
│   ├── __init__.py
│   ├── schemas.py          # Pydantic модели
│   ├── api/                # API роутеры
│   │   ├── __init__.py
│   │   ├── main.py         # Основные endpoints (/health, /stats, etc.)
│   │   └── proxy.py        # Proxy endpoint для микросервисов
│   ├── core/               # Основные компоненты
│   │   ├── __init__.py
│   │   ├── config.py       # Конфигурация из переменных окружения
│   │   └── middleware.py   # Middleware для логирования и статистики
│   └── services/           # Бизнес логика
│       ├── __init__.py
│       ├── proxy.py        # Сервис проксирования запросов
│       └── stats.py        # Сервис сбора статистики
├── requirements.txt
├── Dockerfile
└── README.md
```

## 🚀 Функции

### Маршрутизация
- **Автоматическое определение сервиса** по префиксу URL
- **Проксирование** запросов в соответствующие микросервисы
- **Обработка ошибок** и таймаутов

### Безопасность
- **JWT аутентификация** через auth сервис
- **Публичные endpoints** для login/register
- **Валидация токенов** для приватных запросов
- **CORS настройки**

### Мониторинг
- **Health checks** всех микросервисов
- **Статистика запросов** (количество, время ответа)
- **Подробное логирование** всех операций
- **Метрики производительности**

## 📡 API Endpoints

### Gateway Management
- `GET /` - Информация о системе
- `GET /health` - Состояние всех сервисов
- `GET /stats` - Статистика запросов  
- `GET /routes` - Доступные маршруты
- `POST /stats/reset` - Сброс статистики (dev only)

### Proxy Routes
- `* /auth/*` → auth-service:8000
- `* /events/*` → event-service:8000  
- `* /attendance/*` → attendance-service:8003
- `* /user-statistics/*` → user-statistic-service:8000
- `* /admin/*` → admin-service:8000
- `* /bot/*` → bot-service:8000
- `* /web/*` → web-service:8000

## ⚙️ Конфигурация

### Переменные окружения

```bash
# Основные настройки
SERVICE_NAME=api-gateway
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Сервер
HOST=0.0.0.0
PORT=8000

# Микросервисы
AUTH_SERVICE_URL=http://auth-service:8000
EVENT_SERVICE_URL=http://event-service:8000
ATTENDANCE_SERVICE_URL=http://attendance-service:8003
USER_STATISTIC_SERVICE_URL=http://user-statistic-service:8000
ADMIN_SERVICE_URL=http://admin-service:8000
BOT_SERVICE_URL=http://bot-service:8000
WEB_SERVICE_URL=http://web-service:8000

# Безопасность
JWT_SECRET_KEY=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
CORS_ALLOW_CREDENTIALS=true

# Таймауты
REQUEST_TIMEOUT=30.0
AUTH_TIMEOUT=5.0
HEALTH_CHECK_TIMEOUT=5.0
```

## 🔧 Разработка

### Локальный запуск

```bash
cd services/Gateway

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Установить зависимости
pip install -r requirements.txt

# Запуск в режиме разработки
python main.py
```

### Структура кода

#### `app/core/config.py`
- Класс `Settings` с переменными окружения
- Computed properties для SERVICE_ROUTES
- Конфигурация CORS и безопасности

#### `app/services/proxy.py`
- Класс `ProxyService` для проксирования
- Валидация аутентификации
- Обработка заголовков и ошибок
- Health checks микросервисов

#### `app/services/stats.py`
- Класс `StatsService` для статистики
- Счетчики запросов и времени ответа
- Thread-safe операции

#### `app/core/middleware.py`
- Middleware для логирования
- Измерение времени ответа
- Обновление статистики

#### `app/api/main.py`
- Основные endpoints Gateway
- Health checks и статистика
- Информационные endpoints

#### `app/api/proxy.py`
- Главный proxy endpoint
- Проверка аутентификации
- Маршрутизация запросов

## 🐳 Docker

### Сборка

```bash
# Из корня проекта
docker build -t chupapupa-gateway -f services/Gateway/Dockerfile .
```

### Запуск

```bash
docker run -p 8000:8000 \
  -e AUTH_SERVICE_URL=http://auth:8000 \
  -e EVENT_SERVICE_URL=http://event:8000 \
  chupapupa-gateway
```

## 📊 Мониторинг

### Health Check

```bash
curl http://localhost:8000/health
```

Ответ:
```json
{
  "service": "api-gateway",
  "status": "healthy",
  "version": "2.0.0", 
  "environment": "development",
  "services": {
    "/auth": "healthy",
    "/events": "healthy",
    "/attendance": "unavailable"
  },
  "timestamp": 1703421234.567
}
```

### Статистика

```bash
curl http://localhost:8000/stats
```

Ответ:
```json
{
  "total_requests": 1250,
  "successful_requests": 1180,
  "failed_requests": 70,
  "average_response_time": 0.156
}
```

## 🔒 Безопасность

### Публичные endpoints
- `/health`, `/docs`, `/stats` - доступны всем
- `/auth/login`, `/auth/register` - аутентификация
- Все остальные требуют JWT токен

### Приватные endpoints
- Проверка `Authorization: Bearer <token>`
- Валидация через auth сервис
- 401 Unauthorized при отсутствии/невалидном токене

## 🚨 Troubleshooting

### Частые ошибки

**503 Service Unavailable**
```bash
# Проверить доступность микросервиса
curl http://localhost:8000/health

# Проверить логи
docker logs gateway-container
```

**401 Unauthorized**
```bash
# Проверить токен
curl -H "Authorization: Bearer <token>" http://localhost:8000/auth/verify-token

# Проверить auth сервис
curl http://localhost:8000/health
```

**404 Not Found**
```bash
# Проверить доступные маршруты  
curl http://localhost:8000/routes
```

### Логи

```bash
# Уровни логирования
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR

# Формат логов
2024-12-14 10:30:15,123 - api-gateway - INFO - 🔵 GET /health - Client: 172.18.0.1
2024-12-14 10:30:15,125 - api-gateway - INFO - 🟢 GET /health - 200 - 0.002s
```

## 📈 Производительность

- **Async/await** для неблокирующих операций
- **Connection pooling** в httpx клиенте
- **Таймауты** для предотвращения блокировок
- **Статистика** для мониторинга производительности

## 🔄 Масштабирование

- **Stateless** архитектура
- **Horizontal scaling** через load balancer  
- **Health checks** для автоматического восстановления
- **Circuit breaker pattern** (планируется)