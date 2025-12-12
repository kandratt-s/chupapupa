# Миграции Alembic

## Быстрый запуск
- Поднять базу: `docker-compose up -d postgres` (init-scripts выполнит схемы/права, volume `postgres_data` хранит данные).
- Применить миграции сервиса:
  - Event: `docker-compose run --rm event-service alembic upgrade head`
  - Attendance: `docker-compose run --rm attendance-service alembic upgrade head`
  - Admin/Auth/UserStatistic — аналогично, если появятся версии.
- Проверить в БД: `docker exec postgres-main psql -U chupapupa -d chupapupa_pj -c "\dt event_service.*"` (или нужная схема) — должны быть таблицы и `alembic_version`.

## Создание новой миграции
1. Обновить модели.
2. Сгенерировать ревизию: `docker-compose run --rm <service> alembic revision --autogenerate -m "msg"`.
3. Просмотреть/дополнить файл в `services/<service>/alembic/versions`.
4. Применить: `docker-compose run --rm <service> alembic upgrade head`.

## Полный сброс (если менялись init-scripts или нужно «с чистого листа»)
```bash
docker-compose down -v
docker-compose up -d postgres
docker-compose run --rm event-service alembic upgrade head
docker-compose run --rm attendance-service alembic upgrade head
# при необходимости — остальные сервисы
```

## На старте сервисов
- В .env сервисов оставьте `RUN_MIGRATIONS=true`, тогда при `docker-compose up <service>` миграции выполняются автоматически.
