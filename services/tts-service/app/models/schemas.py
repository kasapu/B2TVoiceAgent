"""Pydantic schemas for TTS service API."""

from pydantic import BaseModel, Field, validator
from typing import Optional
from app.core.config import settings


class SynthesizeRequest(BaseModel):
    """Request model for speech synthesis."""
    text: str = Field(..., description="Text to synthesize", min_length=1, max_length=1000)
    voice: Optional[str] = Field(default="default", description="Voice ID to use")
    speed: Optional[float] = Field(default=1.0, description="Speech speed multiplier (0.5-2.0)", ge=0.5, le=2.0)
    language: Optional[str] = Field(default="en", description="Language code")

    @validator('text')
    def validate_text(cls, v):
        """Validate text is not empty after stripping."""
        if not v.strip():
            raise ValueError("Text cannot be empty")
        if len(v) > settings.MAX_TEXT_LENGTH:
            raise ValueError(f"Text exceeds maximum length of {settings.MAX_TEXT_LENGTH} characters")
        return v.strip()


class SynthesizeResponse(BaseModel):
    """Response model for speech synthesis."""
    audio_url: str = Field(description="Presigned URL to download audio file")
    duration_ms: int = Field(description="Audio duration in milliseconds")
    processing_time_ms: int = Field(description="Processing time in milliseconds")
    text: str = Field(description="Text that was synthesized")
    voice: str = Field(description="Voice ID used")
    format: str = Field(description="Audio format (wav/mp3)")
    sample_rate: int = Field(description="Audio sample rate in Hz")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(description="Service status")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    model: str = Field(description="TTS model being used")
    device: str = Field(description="Compute device (cpu/cuda)")
    device_info: dict = Field(description="Detailed device information")
    minio_connected: bool = Field(description="MinIO storage connection status")
    available_voices: list = Field(description="List of available voice IDs")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
