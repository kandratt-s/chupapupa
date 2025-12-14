-- ===================================================================
-- Создание схемы и таблиц для Attendance Service
-- ===================================================================

-- Создаем схему для attendance сервиса
CREATE SCHEMA IF NOT EXISTS attendance_service;

-- Устанавливаем схему по умолчанию
SET search_path TO attendance_service;

-- Создаем ENUM для статуса заявки
CREATE TYPE attendance_status AS ENUM ('pending', 'approved', 'rejected', 'reviewing');

-- Создаем таблицу записей посещаемости
CREATE TABLE IF NOT EXISTS attendance_records (
    attendance_id SERIAL PRIMARY KEY,
    event_id INT NOT NULL,
    user_id INT NOT NULL,
    photo_path VARCHAR(500),
    is_aproved BOOLEAN NOT NULL DEFAULT FALSE,
    status attendance_status NOT NULL DEFAULT 'pending',
    reviewed_by INT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checked_at TIMESTAMPTZ,

    -- Foreign key constraints
    CONSTRAINT fk_attendance_event
        FOREIGN KEY (event_id) REFERENCES event_service.events (event_id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_user
        FOREIGN KEY (user_id) REFERENCES public.users (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_reviewer
        FOREIGN KEY (reviewed_by) REFERENCES public.users (user_id) ON DELETE SET NULL
);

-- Создаем индексы
CREATE INDEX IF NOT EXISTS idx_attendance_records_event_id ON attendance_records(event_id);
CREATE INDEX IF NOT EXISTS idx_attendance_records_user_id ON attendance_records(user_id);
CREATE INDEX IF NOT EXISTS idx_attendance_records_status ON attendance_records(status);
CREATE INDEX IF NOT EXISTS idx_attendance_records_reviewed_by ON attendance_records(reviewed_by);

-- Комментарии
COMMENT ON TABLE attendance_records IS 'Записи о посещаемости мероприятий студентами';
COMMENT ON COLUMN attendance_records.attendance_id IS 'Главный ключ таблицы';
COMMENT ON COLUMN attendance_records.event_id IS 'Референс к event таблице';
COMMENT ON COLUMN attendance_records.user_id IS 'Референс к users таблице';
COMMENT ON COLUMN attendance_records.photo_path IS 'Путь к фотографии с мероприятия';
COMMENT ON COLUMN attendance_records.is_aproved IS 'Флаг одобрения заявки';
COMMENT ON COLUMN attendance_records.status IS 'Статус рассмотрения заявки';
COMMENT ON COLUMN attendance_records.reviewed_by IS 'ID администратора, рассматривающего заявку';
COMMENT ON COLUMN attendance_records.notes IS 'Дополнительные заметки';
COMMENT ON COLUMN attendance_records.created_at IS 'Дата создания записи';
COMMENT ON COLUMN attendance_records.checked_at IS 'Дата проверки записи';
