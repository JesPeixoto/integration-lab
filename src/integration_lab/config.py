from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "integration-lab"
    api_key: str = "dev-api-key"
    erp_base_url: str = "http://localhost:8001"
    erp_api_key: str = "dev-erp-key"
    erp_timeout_seconds: float = 5.0
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
