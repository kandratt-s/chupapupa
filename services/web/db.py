from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://web_user:web_pass@localhost:5432/chupapupa_pj"
    schema_name: str = "web_service"


settings = DatabaseSettings()
