"""
Data Models and Schemas for SIP Gateway
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class CallState(str, Enum):
    """SIP Call state"""
    IDLE = "idle"
    RINGING = "ringing"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    BRIDGING = "bridging"
    BRIDGED = "bridged"
    STREAMING = "streaming"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class ESLEventType(str, Enum):
    """FreeSWITCH Event Socket Layer event types"""
    CHANNEL_CREATE = "CHANNEL_CREATE"
    CHANNEL_ANSWER = "CHANNEL_ANSWER"
    CHANNEL_BRIDGE = "CHANNEL_BRIDGE"
    CHANNEL_HANGUP = "CHANNEL_HANGUP"
    CHANNEL_DESTROY = "CHANNEL_DESTROY"
    DTMF = "DTMF"
    CUSTOM = "CUSTOM"


class SIPCallInfo(BaseModel):
    """SIP Call Information"""
    call_id: str = Field(..., description="Unique SIP call ID")
    sip_call_id: str = Field(..., description="SIP protocol call ID")
    session_id: Optional[str] = Field(None, description="Voice Connector session ID")
    caller_number: str = Field(..., description="Caller phone number")
    callee_number: str = Field(..., description="Called phone number")
    state: CallState = Field(CallState.IDLE, description="Current call state")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class ESLEvent(BaseModel):
    """FreeSWITCH ESL Event"""
    event_type: str
    unique_id: str
    caller_number: Optional[str] = None
    callee_number: Optional[str] = None
    call_state: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str
    freeswitch_connected: bool
    voice_connector_connected: bool
    active_calls: int
    sip_trunk_status: str


class ActiveCallsResponse(BaseModel):
    """Active calls response"""
    active_calls: int
    calls: list[SIPCallInfo]


class CallMetrics(BaseModel):
    """Call metrics and statistics"""
    total_calls: int = 0
    active_calls: int = 0
    completed_calls: int = 0
    failed_calls: int = 0
    average_duration_seconds: float = 0.0
    total_duration_seconds: float = 0.0


class AudioChunk(BaseModel):
    """Audio data chunk"""
    data: bytes
    sample_rate: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BridgeStatus(BaseModel):
    """Bridge status information"""
    call_id: str
    state: CallState
    is_streaming: bool
    websocket_connected: bool
    freeswitch_connected: bool
    duration_seconds: float
