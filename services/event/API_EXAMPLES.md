# Event Service API Examples

## Функционал Event Service

Event сервис предоставляет полноценное управление мероприятиями с следующими возможностями:

### Доступность функций:
- **Создание мероприятия** - только админ (`POST /admin/events`)
- **Редактирование мероприятия** - только админ (`PUT /admin/events/{event_id}`)
- **Просмотр списка мероприятий** - пользователь/админ (`GET /events`, `GET /admin/events`)

## Базовая структура мероприятия

```json
{
  "event_id": 1,
  "name": "Конференция по IT",
  "date": "2024-12-25T10:00:00",
  "profilnoe": "IT и технологии",
  "opisanie": "Описание мероприятия",
  "active": true
}
```

## API Endpoints

### 1. Получить список мероприятий (пользователь)
```bash
GET /events?limit=10&skip=0&sort_by_date=desc
```

### 2. Поиск по названию
```bash
GET /events?search=конференция
```

### 3. Поиск по ID
```bash
GET /events?search_by_id=5
```

### 4. Поиск по дате
```bash
GET /events?search_by_date=2024-12-25T00:00:00
```

### 5. Фильтр по диапазону дат
```bash
GET /events?date_from=2024-12-01T00:00:00&date_to=2024-12-31T23:59:59
```

### 6. Фильтр по активности
```bash
# Все мероприятия (активные и неактивные)
GET /events?is_active_only=

# Только активные
GET /events?is_active_only=true

# Только неактивные
GET /events?is_active_only=false
```

### 7. Сортировка по дате
```bash
# По убыванию (новые первые)
GET /events?sort_by_date=desc

# По возрастанию (старые первые)
GET /events?sort_by_date=asc
```

### 8. Комплексный поиск
```bash
GET /events?search=IT&date_from=2024-12-01T00:00:00&is_active_only=true&sort_by_date=asc&limit=20
```

## Административные функции

### 1. Создать мероприятие (только админ)
```bash
POST /admin/events
Content-Type: application/json

{
  "name": "Новое мероприятие",
  "date": "2024-12-30T15:00:00",
  "profilnoe": "Образование",
  "opisanie": "Подробное описание",
  "active": true
}
```

### 2. Редактировать мероприятие (только админ)
```bash
PUT /admin/events/1
Content-Type: application/json

{
  "name": "Обновленное название",
  "active": false
}
```

### 3. Административный поиск (включая неактивные)
```bash
GET /admin/events?include_inactive=true&search_by_id=1
```

### 4. Удалить мероприятие (только админ)
```bash
# Мягкое удаление (устанавливает active = false)
DELETE /admin/events/1

# Жесткое удаление (полностью удаляет из БД)
DELETE /admin/events/1?hard_delete=true
```

## Примеры ответов

### Список мероприятий
```json
{
  "events": [
    {
      "event_id": 1,
      "name": "IT Конференция",
      "date": "2024-12-25T10:00:00",
      "profilnoe": "Информационные технологии",
      "opisanie": "Большая IT конференция",
      "active": true
    }
  ],
  "total": 15,
  "page": 1,
  "per_page": 10,
  "total_pages": 2
}
```

### Одно мероприятие
```json
{
  "event_id": 1,
  "name": "IT Конференция",
  "date": "2024-12-25T10:00:00",
  "profilnoe": "Информационные технологии",
  "opisanie": "Большая IT конференция",
  "active": true
}
```

## Заголовки аутентификации

Все запросы требуют следующие заголовки от Gateway:
```
X-User-ID: 123
X-User-Role: user  # или admin
X-Telegram-ID: 456789
```

## Примеры использования curl

```bash
# Получить активные мероприятия
curl -X GET "http://localhost:8003/events?is_active_only=true" \
  -H "X-User-ID: 123" \
  -H "X-User-Role: user" \
  -H "X-Telegram-ID: 456789"

# Создать мероприятие (админ)
curl -X POST "http://localhost:8003/admin/events" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 1" \
  -H "X-User-Role: admin" \
  -H "X-Telegram-ID: 123456" \
  -d '{
    "name": "Новая встреча",
    "date": "2024-12-30T18:00:00",
    "profilnoe": "Нетворкинг",
    "opisanie": "Встреча для общения",
    "active": true
  }'
```
