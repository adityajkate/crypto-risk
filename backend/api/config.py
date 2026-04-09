"""Configuration settings for the API."""
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API configuration settings."""

    # API Keys
    coingecko_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # Rate Limiting
    rate_limit_delay: float = 1.0

    # Model Paths
    artifacts_dir: str = "models"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
