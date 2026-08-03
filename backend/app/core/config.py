from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, PositiveInt
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
    bse_api_base_url: HttpUrl = HttpUrl("https://api.bseindia.com/BseIndiaAPI/api")
    bse_site_base_url: HttpUrl = HttpUrl("https://www.bseindia.com")
    bse_attachment_base_url: HttpUrl = HttpUrl(
        "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"
    )
    user_agent: str = "MarketLensAI/0.1 (educational project; contact: local-developer)"
    http_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    http_read_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    http_write_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    http_pool_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    provider_max_results: PositiveInt = Field(default=20, le=100)
    max_download_bytes: PositiveInt = Field(default=15 * 1024 * 1024, le=50 * 1024 * 1024)
    max_pdf_pages: PositiveInt = Field(default=100, le=500)
    max_redirects: int = Field(default=3, ge=0, le=5)
    market_data_timeout_seconds: float = Field(default=15.0, gt=0, le=60)
    market_event_window_days: int = Field(default=7, ge=3, le=15)


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""
    return Settings()
