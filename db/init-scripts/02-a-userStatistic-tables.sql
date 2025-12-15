-- Создание основной таблицы пользователей в public схеме
CREATE TABLE IF NOT EXISTS public.users (
    user_id SERIAL PRIMARY KEY,
    last_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    group_name VARCHAR(20) NOT NULL,
    hse_email VARCHAR(100) UNIQUE NOT NULL,
    tg_id VARCHAR(50) UNIQUE,
    tg_name VARCHAR(100),
    practice_points FLOAT DEFAULT 0.0 NOT NULL,
    photo_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Создание индексов для таблицы пользователей
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(hse_email);
CREATE INDEX IF NOT EXISTS idx_users_tg_id ON public.users(tg_id);

-- Комментарии
COMMENT ON TABLE public.users IS 'Основная таблица пользователей системы';

-- Предварительные права доступа для userStatistic сервиса
GRANT SELECT, INSERT, UPDATE, DELETE ON public.users TO user_statistic_user;
GRANT USAGE, SELECT ON SEQUENCE public.users_user_id_seq TO user_statistic_user;
