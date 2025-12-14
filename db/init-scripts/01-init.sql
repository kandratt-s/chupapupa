CREATE SCHEMA IF NOT EXISTS auth_service;
CREATE USER auth_user WITH PASSWORD 'auth_pass';
-- Даем права на схему
GRANT USAGE, CREATE ON SCHEMA auth_service TO auth_user;
-- Даем права на все таблицы в схеме (существующие и будущие)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth_service TO auth_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth_service TO auth_user;
-- Устанавливаем права по умолчанию для будущих таблиц
ALTER DEFAULT PRIVILEGES IN SCHEMA auth_service GRANT ALL ON TABLES TO auth_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA auth_service GRANT ALL ON SEQUENCES TO auth_user;

CREATE SCHEMA IF NOT EXISTS event_service;
CREATE USER event_user WITH PASSWORD 'event_pass';
GRANT USAGE, CREATE ON SCHEMA event_service TO event_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA event_service TO event_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA event_service TO event_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA event_service GRANT ALL ON TABLES TO event_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA event_service GRANT ALL ON SEQUENCES TO event_user;

CREATE SCHEMA IF NOT EXISTS attendance_service;
CREATE USER attendance_user WITH PASSWORD 'attendance_pass';
GRANT USAGE, CREATE ON SCHEMA attendance_service TO attendance_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA attendance_service TO attendance_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA attendance_service TO attendance_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA attendance_service GRANT ALL ON TABLES TO attendance_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA attendance_service GRANT ALL ON SEQUENCES TO attendance_user;
-- Attendance needs read/reference access to events
GRANT USAGE ON SCHEMA event_service TO attendance_user;
GRANT SELECT, REFERENCES ON ALL TABLES IN SCHEMA event_service TO attendance_user;
ALTER DEFAULT PRIVILEGES FOR ROLE event_user IN SCHEMA event_service
    GRANT SELECT, REFERENCES ON TABLES TO attendance_user;

-- Allow attendance service to read and reference events
GRANT USAGE ON SCHEMA event_service TO attendance_user;
GRANT SELECT, REFERENCES ON ALL TABLES IN SCHEMA event_service TO attendance_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA event_service GRANT SELECT, REFERENCES ON TABLES TO attendance_user;

CREATE SCHEMA IF NOT EXISTS user_statistic_service;
CREATE USER user_statistic_user WITH PASSWORD 'user_statistic_pass';
GRANT USAGE, CREATE ON SCHEMA user_statistic_service TO user_statistic_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA user_statistic_service TO user_statistic_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA user_statistic_service TO user_statistic_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA user_statistic_service GRANT ALL ON TABLES TO user_statistic_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA user_statistic_service GRANT ALL ON SEQUENCES TO user_statistic_user;

CREATE SCHEMA IF NOT EXISTS admin_service;
CREATE USER admin_user WITH PASSWORD 'admin_pass';
GRANT USAGE, CREATE ON SCHEMA admin_service TO admin_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA admin_service TO admin_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA admin_service TO admin_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA admin_service GRANT ALL ON TABLES TO admin_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA admin_service GRANT ALL ON SEQUENCES TO admin_user;

CREATE SCHEMA IF NOT EXISTS cv_service;
CREATE USER cv_user WITH PASSWORD 'cv_pass';
GRANT USAGE, CREATE ON SCHEMA cv_service TO cv_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cv_service TO cv_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA cv_service TO cv_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA cv_service GRANT ALL ON TABLES TO cv_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA cv_service GRANT ALL ON SEQUENCES TO cv_user;
