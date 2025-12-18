-- Создание схемы для auth сервиса
CREATE SCHEMA IF NOT EXISTS auth_service;

-- Переключаемся на схему auth_service
SET search_path TO auth_service;

-- Создание таблицы auth
CREATE TABLE IF NOT EXISTS auth_service.auth (
    user_id INTEGER PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Foreign key на таблицу пользователей из userStatistic схемы
    CONSTRAINT fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE
);

-- Создание индекса для быстрого поиска по user_id
CREATE INDEX IF NOT EXISTS idx_auth_user_id ON auth_service.auth(user_id);

-- Комментарии к таблице и полям
COMMENT ON SCHEMA auth_service IS 'Схема для сервиса аутентификации';
COMMENT ON TABLE auth_service.auth IS 'Таблица для хранения данных аутентификации пользователей';
COMMENT ON COLUMN auth_service.auth.user_id IS 'ID пользователя из таблицы userStatistic';
COMMENT ON COLUMN auth_service.auth.password_hash IS 'Хеш пароля пользователя';
COMMENT ON COLUMN auth_service.auth.role IS 'Роль пользователя: admin или user';

-- Права доступа для auth сервиса
GRANT ALL PRIVILEGES ON SCHEMA auth_service TO auth_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON auth_service.auth TO auth_user;
GRANT SELECT ON public.users TO auth_user;
