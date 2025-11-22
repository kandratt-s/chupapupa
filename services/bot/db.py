from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://bot_user:bot_pass@localhost:5432/chupapupa_pj"
    schema_name: str = "bot_service"


settings = DatabaseSettings()
