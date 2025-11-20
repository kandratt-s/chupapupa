from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://auth_user:auth_pass@localhost:5432/chupapupa_pj"
    schema_name: str = "auth_service"

settings = DatabaseSettings()

