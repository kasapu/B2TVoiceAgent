"""Configuration settings for TTS service."""

from pydantic_settings import BaseSettings
from typing import Literal
import os


class Settings(BaseSettings):
    """TTS Service configuration settings."""

    # Service Info
    SERVICE_NAME: str = "OCP TTS Service"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Text-to-Speech service using gTTS (Google TTS)"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8003
    RELOAD: bool = True
    LOG_LEVEL: str = "INFO"

    # TTS Model Configuration
    TTS_MODEL: str = "tts_models/en/ljspeech/tacotron2-DDC"
    DEVICE: Literal["auto", "cpu", "cuda"] = "auto"
    VOCODER_MODEL: str = ""  # Optional vocoder, empty uses default

    # Audio Output
    SAMPLE_RATE: int = 22050
    OUTPUT_FORMAT: str = "wav"
    AUDIO_QUALITY: Literal["low", "medium", "high"] = "high"

    # Text Processing
    MAX_TEXT_LENGTH: int = 1000
    MIN_TEXT_LENGTH: int = 1

    # Speech Parameters
    DEFAULT_SPEED: float = 1.0
    MIN_SPEED: float = 0.5
    MAX_SPEED: float = 2.0
    DEFAULT_VOICE: str = "default"

    # MinIO Storage Configuration
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "tts-audio"
    MINIO_SECURE: bool = False
    AUDIO_URL_EXPIRY_HOURS: int = 24

    # File Management
    TEMP_DIR: str = "/tmp/tts-output"
    CLEANUP_AFTER_UPLOAD: bool = True

    # Model Storage
    MODEL_DIR: str = "/models/tts"
    MODELS_PATH: str = "/models/tts"

    # Performance
    USE_CUDA: bool = True
    NUM_THREADS: int = 4

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Create directories if they don't exist
os.makedirs(settings.TEMP_DIR, exist_ok=True)
os.makedirs(settings.MODEL_DIR, exist_ok=True)
