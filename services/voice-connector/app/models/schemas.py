"""
Data models and schemas for Voice Connector
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class CallState(str, Enum):
    """Call state enumeration"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    LISTENING = "listening"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class MessageType(str, Enum):
    """WebSocket message types"""
    AUDIO = "audio"
    TEXT = "text"
    CONTROL = "control"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    STATUS = "status"


class VoiceMessage(BaseModel):
    """Voice message structure"""
    type: MessageType
    data: Any
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class AudioChunk(BaseModel):
    """Audio chunk data"""
    audio_data: bytes
    sample_rate: int = 16000
    format: str = "wav"
    duration_ms: Optional[int] = None


class TranscriptionRequest(BaseModel):
    """STT transcription request"""
    audio_data: bytes
    language: str = "en"
    session_id: str


class TranscriptionResponse(BaseModel):
    """STT transcription response"""
    text: str
    language: str
    duration: float
    confidence: Optional[float] = None
    processing_time_ms: int


class SynthesisRequest(BaseModel):
    """TTS synthesis request"""
    text: str
    voice: str = "default"
    speed: float = 1.0
    session_id: str


class SynthesisResponse(BaseModel):
    """TTS synthesis response"""
    audio_url: str
    duration_ms: int
    processing_time_ms: int
    text: str
    format: str = "wav"


class ConversationRequest(BaseModel):
    """Orchestrator conversation request"""
    session_id: str
    user_message: str
    channel: str = "voice"
    metadata: Optional[Dict[str, Any]] = {}


class ConversationResponse(BaseModel):
    """Orchestrator conversation response"""
    response: str
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = {}
    session_id: str
    metadata: Optional[Dict[str, Any]] = {}


class CallInfo(BaseModel):
    """Call information"""
    call_id: str
    session_id: str
    state: CallState
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    turns_count: int = 0
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    active_calls: int
    uptime_seconds: int
    stt_service: str
    tts_service: str
    orchestrator_service: str
