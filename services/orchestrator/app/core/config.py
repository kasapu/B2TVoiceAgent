"""
Configuration management using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    RELOAD: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://ocpuser:ocppassword@localhost:5432/ocplatform"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    SESSION_TIMEOUT_SECONDS: int = 1800  # 30 minutes

    # Security
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Service URLs
    NLU_SERVICE_URL: str = "http://localhost:8001"
    STT_SERVICE_URL: str = "http://localhost:8002"
    TTS_SERVICE_URL: str = "http://localhost:8003"

    # Feature Flags
    ENABLE_VOICE_CHANNEL: bool = False
    ENABLE_CHAT_CHANNEL: bool = True
    ENABLE_API_CHANNEL: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
