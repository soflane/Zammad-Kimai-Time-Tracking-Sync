"""Application configuration management."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.debug and self.log_level.upper() != "TRACE":
            self.log_level = "DEBUG"

    # Database
    database_url: str

    # Security
    secret_key: str
    encryption_key: str
    webhook_secret: str = "your_webhook_secret_here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # CORS
    cors_origins: str = "http://localhost:5173"

    # Admin User
    admin_username: str = "admin"
    admin_password: str = "changeme"

    # Application
    debug: bool = False
    log_level: str = "INFO"
    api_v1_str: str = "/api/v1"

    # Sync
    sync_schedule_hours: int = 6

    # Connector Settings (for demonstration, these would be per-connector in DB)
    zammad_base_url: str = "http://localhost:3000"
    zammad_api_token: str = "your_zammad_api_token"
    kimai_base_url: str = "http://localhost:8001"
    kimai_api_token: str = "your_kimai_api_token"
    kimai_default_project_id: int = 1

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
