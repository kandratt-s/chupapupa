from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    database_url: str = (
        "postgresql+asyncpg://user_statistic_user:user_statistic_pass@localhost:5432/chupapupa_pj"
    )
    schema_name: str = "user_statistic_service"


settings = DatabaseSettings()
