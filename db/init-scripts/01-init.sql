CREATE SCHEMA IF NOT EXISTS auth_service;
CREATE USER auth_user WITH PASSWORD 'auth_pass';
GRANT USAGE ON SCHEMA auth_service TO auth_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA auth_service GRANT ALL ON TABLES TO auth_user;

CREATE SCHEMA IF NOT EXISTS event_service;
CREATE USER event_user WITH PASSWORD 'event_pass';
GRANT USAGE ON SCHEMA event_service TO event_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA event_service GRANT ALL ON TABLES TO event_user;

CREATE SCHEMA IF NOT EXISTS attendance_service;
CREATE USER attendance_user WITH PASSWORD 'attendance_pass';
GRANT USAGE ON SCHEMA attendance_service TO attendance_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA attendance_service GRANT ALL ON TABLES TO attendance_user;

CREATE SCHEMA IF NOT EXISTS user_statistic_service;
CREATE USER user_statistic_user WITH PASSWORD 'user_statistic_pass';
GRANT USAGE ON SCHEMA user_statistic_service TO user_statistic_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA user_statistic_service GRANT ALL ON TABLES TO user_statistic_user;

CREATE SCHEMA IF NOT EXISTS admin_service;
CREATE USER admin_user WITH PASSWORD 'admin_pass';
GRANT USAGE ON SCHEMA admin_service TO admin_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA admin_service GRANT ALL ON TABLES TO admin_user;

CREATE SCHEMA IF NOT EXISTS cv_service;
CREATE USER cv_user WITH PASSWORD 'cv_pass';
GRANT USAGE ON SCHEMA cv_service TO cv_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA cv_service GRANT ALL ON TABLES TO cv_user;

CREATE SCHEMA IF NOT EXISTS bot_service;
CREATE USER bot_user WITH PASSWORD 'bot_pass';
GRANT USAGE ON SCHEMA bot_service TO bot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA bot_service GRANT ALL ON TABLES TO bot_user;

CREATE SCHEMA IF NOT EXISTS web_service;
CREATE USER web_user WITH PASSWORD 'web_pass';
GRANT USAGE ON SCHEMA web_service TO web_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA web_service GRANT ALL ON TABLES TO web_user;
