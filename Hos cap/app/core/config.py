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
    VAPID_KEY: str = ""

    # Security
    SECRET_KEY: str = "729cf39f40801fc730c4f82875f53c15858cf09c704f77a835565f8a02d8478d" # Change in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    DEBUG: bool = False
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
