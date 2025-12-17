"""
Conversation management endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from datetime import datetime
import uuid
import logging
import time

from app.core.database import get_db
from app.core.redis_client import redis_client
from app.models.schemas import (
    SessionStartRequest, SessionResponse,
    UserInputRequest, OrchestratorResponse,
    SessionEndRequest, SessionEndResponse
)
from app.services.session_manager import SessionManager
from app.services.flow_executor import FlowExecutor
from app.services.nlu_client import NLUClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/start", response_model=SessionResponse, status_code=201)
async def start_conversation(
    request: SessionStartRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize a new conversation session

    Creates a new session in the database and Redis,
    returns the initial greeting message.
    """
    session_manager = SessionManager(db, redis_client)

    try:
        # Create session in database and Redis
        session = await session_manager.create_session(
            channel_type=request.channel_type.value,
            caller_id=request.caller_id,
            user_id=request.user_id,
            initial_context=request.initial_context,
            flow_id=request.flow_id
        )

        # Get initial greeting from flow
        flow_executor = FlowExecutor(db, redis_client)
        initial_message = await flow_executor.get_initial_message(
            session["session_id"]
        )

        logger.info(f"Created session {session['session_id']} for channel {request.channel_type}")

        return SessionResponse(
            session_id=session["session_id"],
            channel_type=request.channel_type,
            started_at=session["started_at"],
            initial_message=initial_message,
            initial_audio_url=None  # TODO: Phase 3 - Generate TTS
        )

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.post("/{session_id}/process", response_model=OrchestratorResponse)
async def process_turn(
    session_id: uuid.UUID,
    request: UserInputRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process user input and return bot response

    Main orchestration flow:
    1. Validate session exists
    2. Transcribe audio (if voice) - Phase 3
    3. Run NLU
    4. Execute dialogue flow logic
    5. Call external APIs if needed
    6. Generate response
    7. Convert to speech (if voice) - Phase 3
    8. Update session state
    9. Log to database
    """
    start_time = time.time()

    session_manager = SessionManager(db, redis_client)
    nlu_client = NLUClient()
    flow_executor = FlowExecutor(db, redis_client)

    try:
        # Step 1: Get session context
        session_context = await session_manager.get_session_context(str(session_id))
        if not session_context:
            raise HTTPException(status_code=404, detail="Session not found or expired")

        # Step 2: Transcribe audio (if needed) - TODO: Phase 3
        if request.input_type == "audio":
            raise HTTPException(status_code=501, detail="Voice input not yet implemented (Phase 3)")

        user_text = request.text

        # Step 3: Run NLU
        logger.info(f"Session {session_id}: Processing input: {user_text}")
        nlu_result = await nlu_client.parse(
            text=user_text,
            language=request.language,
            context=session_context.get("slots", {})
        )

        logger.info(f"Session {session_id}: Detected intent: {nlu_result['intent']['name']} ({nlu_result['intent']['confidence']:.2f})")

        # Step 4: Execute dialogue flow
        flow_result = await flow_executor.execute_flow(
            session_id=str(session_id),
            session_context=session_context,
            intent=nlu_result["intent"]["name"],
            entities=nlu_result["entities"]
        )

        # Step 5: External API calls (if needed) - TODO: Phase 2
        if flow_result.get("api_call_needed"):
            logger.info(f"Session {session_id}: API call needed but not yet implemented (Phase 2)")

        # Step 6: Generate response text
        response_text = flow_result["response_text"]

        # Step 7: TTS (if voice channel) - TODO: Phase 3
        audio_url = None

        # Step 8: Update session context in Redis
        turn_number = session_context.get("turn_count", 0) + 1
        await session_manager.update_session_context(
            session_id=str(session_id),
            updates={
                "current_node": flow_result["next_node"],
                "slots": flow_result.get("context_updates", {}),
                "turn_count": turn_number
            }
        )

        # Step 9: Log conversation turn to database
        await session_manager.log_conversation_turn(
            session_id=session_id,
            turn_number=turn_number,
            speaker="user",
            user_input_text=user_text,
            detected_intent=nlu_result["intent"]["name"],
            intent_confidence=nlu_result["intent"]["confidence"],
            extracted_entities=nlu_result["entities"],
            bot_response_text=response_text,
            bot_action=flow_result["next_action"]["action_type"]
        )

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(f"Session {session_id}: Completed turn {turn_number} in {processing_time_ms}ms")

        # Return orchestrated response
        return OrchestratorResponse(
            session_id=session_id,
            turn_number=turn_number,
            nlu=nlu_result,
            response={
                "type": "text",
                "text": response_text,
                "audio_url": audio_url
            },
            next_action=flow_result["next_action"],
            updated_context=flow_result.get("context_updates", {}),
            processing_time_ms=processing_time_ms,
            confidence_score=nlu_result["intent"]["confidence"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session {session_id}: Error processing turn: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process turn: {str(e)}")


@router.post("/{session_id}/end", response_model=SessionEndResponse)
async def end_conversation(
    session_id: uuid.UUID,
    request: SessionEndRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Terminate a conversation session

    Updates the session end time and removes from Redis
    """
    session_manager = SessionManager(db, redis_client)

    try:
        # Get session context before deleting
        session_context = await session_manager.get_session_context(str(session_id))
        if not session_context:
            raise HTTPException(status_code=404, detail="Session not found")

        # End session in database
        result = await session_manager.end_session(
            session_id=session_id,
            reason=request.reason,
            user_feedback=request.user_feedback
        )

        # Delete from Redis
        await redis_client.delete_session(str(session_id))

        logger.info(f"Ended session {session_id}: {request.reason}")

        return SessionEndResponse(
            session_id=session_id,
            duration_seconds=result["duration_seconds"],
            turn_count=result["turn_count"],
            summary={
                "reason": request.reason,
                "turns": result["turn_count"],
                "duration": result["duration_seconds"]
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")


@router.get("/{session_id}/status")
async def get_session_status(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get current session status"""
    session_manager = SessionManager(db, redis_client)

    session_context = await session_manager.get_session_context(str(session_id))
    if not session_context:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    # Get TTL from Redis
    ttl = await redis_client.get_ttl(str(session_id))

    return {
        "session_id": session_id,
        "current_state": session_context.get("current_state"),
        "turn_count": session_context.get("turn_count", 0),
        "ttl_seconds": ttl,
        "slots": session_context.get("slots", {})
    }
