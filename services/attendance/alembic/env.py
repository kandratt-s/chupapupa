import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from db import settings

    database_url = settings.sync_database_url
    schema_name = settings.schema_name
    print(f"Alembic: Using database URL: {database_url}")
    print(f"Alembic: Using schema: {schema_name}")
except ImportError as e:
    print(f"Error importing settings from db.py: {e}")
    database_url = os.getenv(
        "ATTENDANCE_SYNC_DATABASE_URL",
        "postgresql://attendance_user:attendance_pass@postgres:5432/chupapupa_pj",
    )
    schema_name = os.getenv("ATTENDANCE_SCHEMA_NAME", "attendance_service")

config = context.config

config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=schema_name,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        connection.execute(text(f"SET search_path TO {schema_name}"))

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema_name,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
