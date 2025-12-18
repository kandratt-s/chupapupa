-- ===================================================================
-- Создание схемы и таблиц для Event Service
-- ===================================================================

-- Создаем схему для event сервиса
CREATE SCHEMA IF NOT EXISTS event_service;

-- Устанавливаем схему по умолчанию
SET search_path TO event_service;

CREATE TABLE IF NOT EXISTS events (
    event_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    date TIMESTAMPTZ NOT NULL,
    profilnoe BOOLEAN NOT NULL DEFAULT FALSE,
    opisanie TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Права доступа для event сервиса
GRANT ALL PRIVILEGES ON SCHEMA event_service TO event_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON event_service.events TO event_user;
GRANT USAGE, SELECT ON SEQUENCE event_service.events_event_id_seq TO event_user;
GRANT SELECT ON public.users TO event_user;
