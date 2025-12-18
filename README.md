# Chupapupa — Practice Service

Проект — набор микросервисов, веб-интерфейсов и бота для управления мероприятиями, приёма заявок и системы начисления баллов студентам.

# Содержание
- Краткое описание
- Архитектура и сервисы
- Возможности пользователя
- Возможности администратора
- Какие функции/эндпоинты используются (список по файлам)
- Статистика админа
  
---

## Краткое описание

Chupapupa реализует:
- управление мероприятиями (events);
- приём заявок на участие (applications / attendance);
- управление пользователями и систему баллов (userStatistic);
- веб-интерфейс на Streamlit;
- Telegram-бот;
- Gateway — центральный HTTP-прокси для маршрутизации запросов между сервисами.

---

## Архитектура и сервисы — детально

Gateway (services/Gateway/gateway.py)
- Назначение: центральная точка маршрутизации запросов от UI и ботов к внутренним сервисам.
- Как работает: принимает запросы вида /{service}/{path:path} и пересылает их на соответствующий адрес из конфигурации ROUTES, сохраняя заголовки и тело запроса.
- Важно: Gateway не выполняет сам авторизацию — за проверку прав отвечают реальные сервисы (например, userStatistic через dependency `admin_required`).

Сервисы, к которым проксирует Gateway:

1) Auth Service
- Назначение: аутентификация пользователей (веб/бот).
- Основные эндпоинты (используются клиентами):
  - POST /login — вход (возвращает токен/сессию).
- Роль: выдаёт токен/сессии, по ним фронт/боты идентифицируют пользователя и передают заголовки в Gateway.

2) API / Users Service (userStatistic / API)
- Назначение: пользовательские операции (CRUD пользователей) и логика по работе с профилями и баллами.
- Основные эндпоинты:
  - POST /users/create — регистрация пользователя
  - GET /users — список пользователей (админ)
  - GET /users/{id} — получить профиль пользователя
  - DELETE /users/{id} — удалить пользователя
  - PATCH /users/{id}/points — изменить баллы пользователя
- Роль: хранит/возвращает профильную информацию, фото (пути/URL), роль и баллы (points).

3) Events Service
- Назначение: управление мероприятиями.
- Типичные эндпоинты:
  - POST /create — создать мероприятие (name, description, is_profile, date)
  - GET /all — получить все мероприятия
  - GET /active — получить активные мероприятия
  - GET /{event_id} — получить мероприятие по ID
  - POST /{event_id}/deactivate — завершить/деактивировать мероприятие
  - DELETE /{event_id} — удалить мероприятие
- Модель мероприятия (поля, используемые в UI):
  - id, name, description, date, is_active (bool), is_profile (bool)

4) Attendance / Applications Service
- Назначение: приём заявок на мероприятия, их хранение и статусы.
- Основные эндпоинты:
  - POST /create — создать заявку (user_id, event_id, photo_path)
  - GET /user/{user_id} — получить заявки пользователя
  - GET /all — получить все заявки (для админов)
  - POST /{app_id}/approve — одобрить заявку
  - POST /{app_id}/reject — отклонить заявку
- Модель заявки:
  - id, user_id, event_id, status (pending/approved/rejected), created_at, photo_path, event_name, комментарии

5) Statistics Service
- Назначение: агрегированные данные/метрики системы; может предоставлять endpoint `GET /statistics/full` для отдачи заранее посчитанных агрегатов.
- Примеры эндпоинтов:
  - GET /full — вернуть готовые агрегаты (totals, top_events, daily_dynamics и т.д.)
  - POST /add-points (или другой контракт) — начисление баллов в систему
- Роль: централизовать сложные агрегации, чтобы UI не загружал все «сырые» данные.

6) Storage Service
- Назначение: хранение файлов (фото заявок, аватары пользователей), предоставление URL/путей.
- Типичные операции:
  - POST /upload — загрузка файлов
  - GET /files/{id} — получение файла или публичного URL
- UI/боты отправляют фото в Storage, получают ссылку, которую передают в Attendance/create.

7) UserStatistic Service (детальнее, если выделен отдельно)
- Назначение: управление статистикой пользователей (баллы, группы, агрегаты).
- Ключевые CRUD/агрегатные функции (см. services/userStatistic/app/core/crud.py):
  - update_user_points — обновление practice_points
  - get_group_statistics — SQL-агрегации по группам (count, avg, max, min)
  - get_users_list — пагинация, фильтры, поиск
- Admin-эндпоинты защищены dependency `admin_required`.

Интеракция — схема
- Streamlit фронтенд (gateway_web) и Telegram-бот (gateway_bot) отправляют HTTP-запросы в путь вида /{service}/{path} на Gateway.
- Gateway пересылает запрос в соответствующий внутренний сервис.
- Сервис выполняет логику и возвращает JSON; Gateway возвращает результат клиенту.
- Авторизация: токены/сессии передаются в заголовках запросов — внутренние сервисы обязаны проверять авторизацию и роль (admin_required).

---

## Возможности пользователя

Все операции пользователя реализованы через HTTP API и доступны из UI/бота:

- Регистрация / Создание профиля: POST /users/create
- Вход (login): POST /login — возвращает токен/сессию
- Просмотр списка мероприятий: GET /events/active или GET /events/all
- Подача заявки: POST /attendance/create { user_id, event_id, photo_path }
- Просмотр своих заявок: GET /attendance/user/{user_id}
- Просмотр профиля: GET /users/{id}

UI и бот используют клиентские функции из `services/web/gateway_web/api/gateway_client.py` и аналогичные клиенты в боте.

---

## Возможности администратора

Админ-интерфейс реализован в Streamlit и через бот; админские операции включают:

1. Управление пользователями (Users API)
- Получить список всех пользователей (пагинация, поиск, фильтр по активности)
  - Серверная логика: get_users_list (skip/limit/search/is_active_only)
- Создать пользователя (проверка уникальности email/tg_id)
- Обновить профиль пользователя (включая изменение роли и активности)
- Удалить пользователя
- Изменить баллы пользователя (update_user_points)

2. Управление мероприятиями (Events Service)
- Создать мероприятие (name, description, is_profile, date)
- Просматривать список мероприятий, фильтровать по статусу
- Деактивировать (завершить) мероприятие
- Удалить мероприятие

3. Рассмотрение заявок (Attendance Service)
- Просматривать заявки с фильтрами по статусу
- Одобрять и отклонять заявки
- При одобрении инициировать начисление баллов в UserStatistic/Statistics Service

4. Статистика
- Общая статистика: число пользователей, число студентов, число мероприятий, число заявок
- Распределение заявок по статусам (pie chart)
- Популярность мероприятий (топ по числу заявок, bar chart)
- Динамика подачи заявок по датам (line chart)
- Рейтинг студентов по баллам (таблица)
- Метрики эффективности: количество рассмотренных заявок, процент одобрения, средний балл студента и прогресс-бар

5. Права доступа
- UI: перед показом админских view проверяется session["role"] == "admin" (Streamlit session, get_session)
- API: админ-эндпоинты защищены зависимостью admin_required (FastAPI dependency)
- Боты: локальные токены/сессии содержат роль; серверные сервисы дополнительно проверяют права

---

## Какие функции/эндпоинты используются

Ниже — реальные вызовы, которые фронты/боты делают (файлы, использующие эти вызовы указаны рядом):

Gateway client (services/web/gateway_web/api/gateway_client.py)
- Пользователи:
  - POST /api/users/create — api_register_user(name, surname, email, password, role, photo_path)
  - POST /auth/login — api_login(email, password)
  - GET /api/users/{id} — api_get_user(user_id)
  - GET /api/users — api_get_all_users()
  - DELETE /api/users/{id} — api_delete_user(user_id)

- Мероприятия:
  - POST /events/create — api_create_event(name, description, is_profile, date)
  - GET /events/{id} — api_get_event(event_id)
  - GET /events/all — api_get_all_events()
  - POST /events/{id}/deactivate — api_deactivate_event(event_id)
  - DELETE /events/{id} — api_delete_event(event_id)
  - GET /events/active — api_get_active_events()

- Заявки (Attendance):
  - POST /attendance/create — api_create_application(user_id, event_id, photo_path)
  - GET /attendance/user/{user_id} — api_get_my_applications(user_id)
  - GET /attendance/all — api_get_all_applications()
  - POST /attendance/{id}/approve — api_approve_application(app_id)
  - POST /attendance/{id}/reject — api_reject_application(app_id)

- Статистика:
  - GET /statistics/full — api_get_full_statistics()

Боты (services/bot/gateway_bot/handlers/admin_apps.py)
- api_get_pending_applications(token)
- api_get_application(token, id)
- api_approve_application(token, id)
- api_reject_application(token, id)
- api_add_points(token, ...)
- api_get_user(token, user_id)
- api_get_event(token, event_id)

Backend (userStatistic service — services/userStatistic/app/api/admin.py)
- GET /admin/users — получает пользователей с пагинацией/search/active_only
- POST /admin/users — создание пользователя
- PUT /admin/users/{id} — обновление пользователя
- PATCH /admin/users/{id}/points — изменение баллов
- Dependency: admin_required

Backend CRUD (services/userStatistic/app/core/crud.py)
- update_user_points — обновление practice_points
- get_group_statistics — SQL-агрегации по группам (count, avg, max, min)
- get_users_list — поддержка skip/limit/search/is_active_only

Gateway implementation note
- Файл `services/Gateway/gateway.py` содержит простую логику проксирования: запросы вида `/{service}/{path}` перенаправляются на адреса из словаря ROUTES, с сохранением заголовков и тела запроса.

---

## Статистика админа

Админская панель (gateway_web) запрашивает данные у отдельных сервисов и затем формирует метрики:

1. Источники данных (запросы к сервисам)
- GET /attendance/all — все заявки (Attendance Service)
- GET /api/users — все пользователи (Users API / userStatistic)
- GET /events/all — все мероприятия (Events Service)
- GET /events/{id} — детали мероприятия (для получения name/is_profile)

2. Основные показатели
- Число пользователей
- Число студентов
- Число мероприятий
- Число заявок
- pending/approved/rejected
- Активные мероприятия

3. Графики и таблицы
- Pie chart: распределение заявок по статусам
- Bar chart: популярность мероприятий
- Line chart: динамика подачи заявок по датам
- Таблица: рейтинг студентов
- Эффективность рассмотрения
