CREATE SCHEMA IF NOT EXISTS auth_service;

CREATE USER auth_user WITH PASSWORD 'auth_pass';

GRANT USAGE ON SCHEMA auth_service TO auth_user;
