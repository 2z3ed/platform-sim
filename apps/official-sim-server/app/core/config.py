import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


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
    webhook_url: str = os.getenv("WEBHOOK_URL", "")
    webhook_urls: str = os.getenv("WEBHOOK_URLS", "")

    # Order facts source: "fixture" | "odoo"
    order_source_mode: str = os.getenv("ORDER_SOURCE_MODE", "fixture")

    # Odoo connection
    odoo_base_url: str = os.getenv("ODOO_BASE_URL", "http://localhost:8069")
    odoo_db: str = os.getenv("ODOO_DB", "odoo")
    odoo_username: str = os.getenv("ODOO_USERNAME", "admin")
    odoo_api_key: str = os.getenv("ODOO_API_KEY", "")
    odoo_timeout: int = int(os.getenv("ODOO_TIMEOUT", "30"))

    def get_webhook_urls(self) -> List[str]:
        urls = []
        if self.webhook_url:
            urls.append(self.webhook_url)
        if self.webhook_urls:
            urls.extend([u.strip() for u in self.webhook_urls.split(",") if u.strip()])
        return list(set(urls))


settings = Settings()
