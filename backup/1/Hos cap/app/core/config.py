"""
Application configuration loaded from environment variables.
Uses pydantic-settings for validation and .env file support.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    APP_NAME: str = "Hospital Appointment System"

    # PostgreSQL async connection string
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/hospital_db"

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = "firebase-service-account.json"

    # Application
    DEBUG: bool = False

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
