import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/official_sim"
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    service_name: str = "official-sim-server"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    db_echo: bool = os.getenv("DB_ECHO", "false").lower() == "true"


settings = Settings()
