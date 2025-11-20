from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://admin_user:admin_pass@localhost:5432/chupapupa_pj"
    schema_name: str = "admin_service"

settings = DatabaseSettings()

