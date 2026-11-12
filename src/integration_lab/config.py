from functools import lru_cache

from pydantic import Field
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
    erp_max_attempts: int = Field(default=3, ge=1, le=10)
    erp_retry_base_seconds: float = Field(default=0.2, ge=0)
    erp_retry_max_seconds: float = Field(default=2.0, ge=0)
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
