from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    database_url: str = "postgresql+asyncpg://cv_user:cv_pass@localhost:5432/chupapupa_pj"
    schema_name: str = "cv_service"


settings = DatabaseSettings()
