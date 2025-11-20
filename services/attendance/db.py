from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://attendance_user:attendance_pass@localhost:5432/chupapupa_pj"
    schema_name: str = "attendance_service"

settings = DatabaseSettings()

