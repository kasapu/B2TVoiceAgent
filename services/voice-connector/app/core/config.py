"""
Voice Connector Service Configuration
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Service Info
    SERVICE_NAME: str = "OCP Voice Connector"
    VERSION: str = "1.0.0"

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8005"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # STT Service
    STT_SERVICE_URL: str = os.getenv("STT_SERVICE_URL", "http://localhost:8002")

    # TTS Service
    TTS_SERVICE_URL: str = os.getenv("TTS_SERVICE_URL", "http://localhost:8003")

    # Orchestrator Service
    ORCHESTRATOR_URL: str = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")

    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))
    WS_TIMEOUT: int = int(os.getenv("WS_TIMEOUT", "300"))
    MAX_CONNECTIONS: int = int(os.getenv("MAX_CONNECTIONS", "1000"))

    # Audio Configuration
    SAMPLE_RATE: int = int(os.getenv("SAMPLE_RATE", "16000"))
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "4096"))
    AUDIO_FORMAT: str = os.getenv("AUDIO_FORMAT", "wav")

    # Buffer Configuration
    BUFFER_DURATION_MS: int = int(os.getenv("BUFFER_DURATION_MS", "1000"))
    MIN_AUDIO_LENGTH_MS: int = int(os.getenv("MIN_AUDIO_LENGTH_MS", "500"))
    SILENCE_THRESHOLD: float = float(os.getenv("SILENCE_THRESHOLD", "0.01"))
    SILENCE_DURATION_MS: int = int(os.getenv("SILENCE_DURATION_MS", "500"))

    # Performance
    MAX_CONCURRENT_CALLS: int = int(os.getenv("MAX_CONCURRENT_CALLS", "100"))
    AUDIO_TIMEOUT_SECONDS: int = int(os.getenv("AUDIO_TIMEOUT_SECONDS", "10"))

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
