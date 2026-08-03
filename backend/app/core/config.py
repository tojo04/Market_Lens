from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings for the API scaffold."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MARKETLENS_",
        extra="ignore",
    )

    app_name: str = "MarketLens AI API"
    environment: Literal["development", "test", "production"] = "development"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""
    return Settings()
