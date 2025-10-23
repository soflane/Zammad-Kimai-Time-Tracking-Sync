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

    # Database
    database_url: str

    # Security
    secret_key: str
    encryption_key: str
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

    # Sync
    sync_schedule_hours: int = 6

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
