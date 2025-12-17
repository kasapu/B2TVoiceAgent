"""Configuration settings for STT service."""

from pydantic_settings import BaseSettings
from typing import Literal
import os


class Settings(BaseSettings):
    """STT Service configuration settings."""

    # Service Info
    SERVICE_NAME: str = "OCP STT Service"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Speech-to-Text service using OpenAI Whisper"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    RELOAD: bool = True
    LOG_LEVEL: str = "INFO"

    # Whisper Model Configuration
    WHISPER_MODEL: Literal["tiny", "base", "small", "medium", "large"] = "base"
    DEVICE: Literal["auto", "cpu", "cuda"] = "auto"
    COMPUTE_TYPE: Literal["auto", "int8", "float16", "float32"] = "auto"

    # Audio Processing
    SAMPLE_RATE: int = 16000
    MAX_FILE_SIZE_MB: int = 25
    SUPPORTED_FORMATS: list[str] = ["wav", "mp3", "m4a", "flac", "ogg", "webm"]

    # Transcription Parameters
    BEAM_SIZE: int = 5
    BEST_OF: int = 5
    TEMPERATURE: float = 0.0
    VAD_FILTER: bool = True
    VAD_THRESHOLD: float = 0.5

    # File Management
    TEMP_DIR: str = "/tmp/stt-uploads"
    CLEANUP_AFTER_TRANSCRIBE: bool = True

    # Model Storage
    MODEL_DIR: str = "/models/stt"
    DOWNLOAD_ROOT: str = "/models/stt"

    # Performance
    NUM_WORKERS: int = 1
    CPU_THREADS: int = 4

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Create temp directory if it doesn't exist
os.makedirs(settings.TEMP_DIR, exist_ok=True)
os.makedirs(settings.MODEL_DIR, exist_ok=True)
