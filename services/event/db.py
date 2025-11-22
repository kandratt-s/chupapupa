from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://event_user:event_pass@localhost:5432/chupapupa_pj"
    schema_name: str = "event_service"


settings = DatabaseSettings()
