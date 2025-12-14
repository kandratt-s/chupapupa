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
