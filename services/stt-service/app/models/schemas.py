"""Pydantic schemas for STT service API."""

from pydantic import BaseModel, Field
from typing import Optional, List


class TranscribeRequest(BaseModel):
    """Request model for transcription (form data)."""
    language: Optional[str] = Field(default="en", description="Language code (e.g., 'en', 'es', 'fr')")
    task: Optional[str] = Field(default="transcribe", description="Task: 'transcribe' or 'translate'")
    beam_size: Optional[int] = Field(default=5, description="Beam size for decoding")
    temperature: Optional[float] = Field(default=0.0, description="Temperature for sampling")


class Segment(BaseModel):
    """A segment of transcribed text with timing."""
    id: int = Field(description="Segment ID")
    start: float = Field(description="Start time in seconds")
    end: float = Field(description="End time in seconds")
    text: str = Field(description="Transcribed text")


class TranscribeResponse(BaseModel):
    """Response model for transcription."""
    text: str = Field(description="Full transcribed text")
    language: str = Field(description="Detected language code")
    duration: float = Field(description="Audio duration in seconds")
    segments: Optional[List[Segment]] = Field(default=None, description="Text segments with timestamps")
    processing_time_ms: int = Field(description="Processing time in milliseconds")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(description="Service status")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    model: str = Field(description="Whisper model being used")
    device: str = Field(description="Compute device (cpu/cuda)")
    device_info: dict = Field(description="Detailed device information")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
