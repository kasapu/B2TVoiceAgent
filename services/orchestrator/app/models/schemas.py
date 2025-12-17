"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel, Field, UUID4
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


# ============================================
# ENUMS
# ============================================

class ChannelType(str, Enum):
    """Conversation channel types"""
    VOICE = "voice"
    CHAT = "chat"
    API = "api"


class InputType(str, Enum):
    """User input types"""
    TEXT = "text"
    AUDIO = "audio"


class Speaker(str, Enum):
    """Conversation turn speaker"""
    USER = "user"
    BOT = "bot"
    AGENT = "agent"


class ActionType(str, Enum):
    """Next action types"""
    CONTINUE = "continue"
    WAIT_FOR_INPUT = "wait_for_input"
    TRANSFER_TO_AGENT = "transfer_to_agent"
    END_CONVERSATION = "end_conversation"
    EXECUTE_API_CALL = "execute_api_call"


# ============================================
# SESSION MODELS
# ============================================

class SessionStartRequest(BaseModel):
    """Request to start a new conversation session"""
    channel_type: ChannelType
    caller_id: Optional[str] = None
    user_id: Optional[UUID4] = None
    initial_context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    flow_id: Optional[UUID4] = None


class SessionResponse(BaseModel):
    """Response for session creation"""
    session_id: UUID4
    channel_type: ChannelType
    started_at: datetime
    initial_message: str
    initial_audio_url: Optional[str] = None


# ============================================
# CONVERSATION MODELS
# ============================================

class UserInputRequest(BaseModel):
    """Request to process user input"""
    input_type: InputType
    text: Optional[str] = None
    audio_url: Optional[str] = None
    language: str = "en-US"
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class NLUResult(BaseModel):
    """NLU parsing result"""

    class Intent(BaseModel):
        name: str
        confidence: float

    class Entity(BaseModel):
        entity_type: str
        value: str
        confidence: float
        start_char: Optional[int] = None
        end_char: Optional[int] = None

    class Sentiment(BaseModel):
        label: str  # positive, neutral, negative
        score: float

    intent: Intent
    entities: List[Entity] = Field(default_factory=list)
    sentiment: Optional[Sentiment] = None


class NextAction(BaseModel):
    """Next action to take in conversation"""
    action_type: ActionType
    action_config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class BotResponse(BaseModel):
    """Bot response to user"""
    type: str  # text, audio, adaptive_card
    text: str
    audio_url: Optional[str] = None
    ssml: Optional[str] = None


class OrchestratorResponse(BaseModel):
    """Complete response from orchestrator"""
    session_id: UUID4
    turn_number: int
    nlu: NLUResult
    response: BotResponse
    next_action: NextAction
    updated_context: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: int
    confidence_score: float


class SessionEndRequest(BaseModel):
    """Request to end a session"""
    reason: str  # completed, abandoned, transferred, error
    user_feedback: Optional[Dict[str, Any]] = None


class SessionEndResponse(BaseModel):
    """Response for session termination"""
    session_id: UUID4
    duration_seconds: int
    turn_count: int
    summary: Dict[str, Any]


# ============================================
# FLOW MODELS
# ============================================

class DialogueFlowCreate(BaseModel):
    """Request to create a dialogue flow"""
    flow_name: str
    description: Optional[str] = None
    flow_definition: Dict[str, Any]
    traffic_percentage: int = Field(default=100, ge=0, le=100)


class DialogueFlow(BaseModel):
    """Dialogue flow response"""
    flow_id: UUID4
    flow_name: str
    version: int
    is_active: bool
    flow_definition: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FlowPublishRequest(BaseModel):
    """Request to publish a flow"""
    traffic_percentage: int = Field(default=100, ge=0, le=100)


# ============================================
# NLU MODELS
# ============================================

class NLUParseRequest(BaseModel):
    """Standalone NLU parse request"""
    text: str
    language: str = "en-US"
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ============================================
# HEALTH CHECK
# ============================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    environment: str
    database: str
    redis: str
    timestamp: datetime
