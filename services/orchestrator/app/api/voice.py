"""
Voice Channel API Endpoints
Simplified endpoints for voice connector integration
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import logging

from app.core.database import get_db
from app.core.redis_client import redis_client
from app.services.session_manager import SessionManager
from app.services.flow_executor import FlowExecutor
from app.services.nlu_client import NLUClient

router = APIRouter()
logger = logging.getLogger(__name__)


class SessionCreateRequest(BaseModel):
    """Request to create a new session"""
    channel: str = "voice"


class SessionCreateResponse(BaseModel):
    """Response with new session ID"""
    session_id: str


class ConversationRequest(BaseModel):
    """Request to send a message"""
    session_id: str
    user_message: str
    channel: str = "voice"
    metadata: Optional[Dict[str, Any]] = {}


class ConversationResponse(BaseModel):
    """Response with bot message"""
    response: str
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = {}
    session_id: str
    metadata: Optional[Dict[str, Any]] = {}


@router.post("/session", response_model=SessionCreateResponse)
async def create_session(
    request: SessionCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new conversation session for voice

    This is a simplified endpoint specifically for voice connector.
    """
    session_manager = SessionManager(db, redis_client)

    try:
        # Create session
        session = await session_manager.create_session(
            channel_type=request.channel,
            caller_id=None,
            user_id=None,
            initial_context={},
            flow_id=None  # Use default flow
        )

        logger.info(f"Created voice session {session['session_id']}")

        return SessionCreateResponse(
            session_id=session["session_id"]
        )

    except Exception as e:
        logger.error(f"Failed to create voice session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}"
        )


@router.post("/conversation", response_model=ConversationResponse)
async def process_conversation(
    request: ConversationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a conversation turn

    Simplified endpoint for voice connector:
    - Takes session_id and user_message
    - Returns bot response text
    """
    session_manager = SessionManager(db, redis_client)
    nlu_client = NLUClient()
    flow_executor = FlowExecutor(db, redis_client)

    try:
        # Get session context
        session_context = await session_manager.get_session_context(
            request.session_id
        )

        if not session_context:
            raise HTTPException(
                status_code=404,
                detail="Session not found or expired"
            )

        # Run NLU
        logger.info(
            f"Voice session {request.session_id}: "
            f"Processing: {request.user_message}"
        )

        nlu_result = await nlu_client.parse(
            text=request.user_message,
            language="en",
            context=session_context.get("slots", {})
        )

        intent_name = nlu_result["intent"]["name"]
        confidence = nlu_result["intent"]["confidence"]

        logger.info(
            f"Voice session {request.session_id}: "
            f"Intent: {intent_name} ({confidence:.2f})"
        )

        # Execute dialogue flow
        flow_result = await flow_executor.execute_flow(
            session_id=request.session_id,
            session_context=session_context,
            intent=intent_name,
            entities=nlu_result["entities"]
        )

        response_text = flow_result["response_text"]

        # Update session context
        turn_number = session_context.get("turn_count", 0) + 1
        await session_manager.update_session_context(
            session_id=request.session_id,
            updates={
                "current_node": flow_result["next_node"],
                "slots": flow_result.get("context_updates", {}),
                "turn_count": turn_number
            }
        )

        # Log conversation turn
        await session_manager.log_conversation_turn(
            session_id=uuid.UUID(request.session_id),
            turn_number=turn_number,
            speaker="user",
            user_input_text=request.user_message,
            detected_intent=intent_name,
            intent_confidence=confidence,
            extracted_entities=nlu_result["entities"],
            bot_response_text=response_text,
            bot_action=flow_result["next_action"]["action_type"]
        )

        logger.info(
            f"Voice session {request.session_id}: "
            f"Response: {response_text}"
        )

        return ConversationResponse(
            response=response_text,
            intent=intent_name,
            entities=nlu_result["entities"],
            session_id=request.session_id,
            metadata={
                "confidence": confidence,
                "turn_number": turn_number
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Voice session {request.session_id}: "
            f"Error: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )
