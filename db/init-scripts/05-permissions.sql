-- ===================================================================
-- Права доступа для всех сервисов к базе данных
-- ===================================================================

-- ===========================================
-- ПРАВА ДЛЯ USERSTATISTIC SERVICE
-- ===========================================
-- Доступ к таблице users в public схеме
GRANT SELECT, INSERT, UPDATE, DELETE ON public.users TO user_statistic_user;
GRANT USAGE, SELECT ON SEQUENCE public.users_user_id_seq TO user_statistic_user;
GRANT USAGE, CREATE ON SCHEMA public TO user_statistic_user;

-- ===========================================
-- ПРАВА ДЛЯ AUTH SERVICE
-- ===========================================
-- Доступ к своей схеме auth_service
GRANT ALL PRIVILEGES ON SCHEMA auth_service TO auth_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON auth_service.auth TO auth_user;

-- Доступ на чтение пользователей для проверки существования
GRANT SELECT ON public.users TO auth_user;

-- ===========================================
-- ПРАВА ДЛЯ EVENT SERVICE
-- ===========================================
-- Доступ к своей схеме event_service
GRANT ALL PRIVILEGES ON SCHEMA event_service TO event_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON event_service.events TO event_user;
GRANT USAGE, SELECT ON SEQUENCE event_service.events_event_id_seq TO event_user;

-- Доступ на чтение пользователей для проверки создателя событий
GRANT SELECT ON public.users TO event_user;

-- ===========================================
-- ПРАВА ДЛЯ ATTENDANCE SERVICE
-- ===========================================
-- Доступ к своей схеме attendance_service
GRANT ALL PRIVILEGES ON SCHEMA attendance_service TO attendance_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON attendance_service.attendance_records TO attendance_user;
GRANT USAGE, SELECT ON SEQUENCE attendance_service.attendance_records_attendance_id_seq TO attendance_user;

-- Доступ на чтение пользователей и событий
GRANT SELECT ON public.users TO attendance_user;
GRANT SELECT ON event_service.events TO attendance_user;

-- ===========================================
-- ПРАВА ДЛЯ ADMIN SERVICE (если используется)
-- ===========================================
-- Админ должен иметь доступ ко всем таблицам для управления
GRANT SELECT, INSERT, UPDATE, DELETE ON public.users TO admin_user;
GRANT USAGE, SELECT ON SEQUENCE public.users_user_id_seq TO admin_user;

GRANT SELECT, INSERT, UPDATE, DELETE ON auth_service.auth TO admin_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON event_service.events TO admin_user;
GRANT USAGE, SELECT ON SEQUENCE event_service.events_event_id_seq TO admin_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON attendance_service.attendance_records TO admin_user;
GRANT USAGE, SELECT ON SEQUENCE attendance_service.attendance_records_attendance_id_seq TO admin_user;

-- ===========================================
-- КРОСС-СЕРВИСНЫЕ ПРАВА
-- ===========================================
-- UserStatistic сервису нужен доступ для обновления баллов при одобрении заявок
-- (уже есть выше)

-- Attendance сервису нужен доступ для проверки событий
-- (уже есть выше)

-- Auth сервису нужен доступ для проверки пользователей
-- (уже есть выше)

-- ===========================================
-- ПРАВА НА СХЕМЫ
-- ===========================================
-- Разрешаем использование схем
GRANT USAGE ON SCHEMA public TO user_statistic_user, auth_user, event_user, attendance_user, admin_user;
GRANT USAGE ON SCHEMA auth_service TO auth_user, admin_user;
GRANT USAGE ON SCHEMA event_service TO event_user, attendance_user, admin_user;
GRANT USAGE ON SCHEMA attendance_service TO attendance_user, admin_user;
GRANT USAGE ON SCHEMA user_statistic_service TO user_statistic_user, admin_user;

-- ===========================================
-- ДОПОЛНИТЕЛЬНЫЕ ПРАВА ДЛЯ ИНТЕГРАЦИИ
-- ===========================================
-- UserStatistic сервису для интеграции с Attendance (начисление баллов)
-- Уже есть полные права на users выше

-- Attendance сервису для проверки прав пользователей через UserStatistic
-- Уже есть права на чтение users выше

-- Логирование успешного применения прав
SELECT 'Database permissions successfully granted to all services!' as status;
