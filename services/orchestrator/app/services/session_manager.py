"""
Session management service
Handles session creation, retrieval, and updates
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, Dict, Any
import uuid
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages conversation sessions in database and Redis"""

    def __init__(self, db: AsyncSession, redis_client):
        self.db = db
        self.redis = redis_client

    async def create_session(
        self,
        channel_type: str,
        caller_id: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        flow_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation session

        Args:
            channel_type: Type of channel (voice, chat, api)
            caller_id: Caller identifier (phone number for voice)
            user_id: User UUID if authenticated
            initial_context: Initial context values
            flow_id: Specific flow to use (defaults to active flow)

        Returns:
            Session dictionary with session_id and metadata
        """
        session_id = uuid.uuid4()
        started_at = datetime.utcnow()

        # If no flow specified, get the active flow
        if not flow_id:
            result = await self.db.execute(
                text("SELECT flow_id FROM dialogue_flows WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 1")
            )
            row = result.fetchone()
            if row:
                flow_id = row[0]

        # Insert session into database
        await self.db.execute(
            text("""
            INSERT INTO sessions (
                session_id, channel_type, caller_id, user_id,
                started_at, current_state, context, assigned_flow_id
            ) VALUES (
                :session_id, :channel_type, :caller_id, :user_id,
                :started_at, 'started', CAST(:context AS jsonb), :flow_id
            )
            """),
            {
                "session_id": session_id,
                "channel_type": channel_type,
                "caller_id": caller_id,
                "user_id": user_id,
                "started_at": started_at,
                "context": json.dumps(initial_context or {}),
                "flow_id": flow_id
            }
        )
        await self.db.commit()

        # Store session context in Redis
        session_context = {
            "session_id": str(session_id),
            "channel_type": channel_type,
            "current_node": "start",
            "current_state": "started",
            "slots": initial_context or {},
            "turn_count": 0,
            "started_at": started_at.isoformat(),
            "flow_id": str(flow_id) if flow_id else None
        }

        await self.redis.set_session(str(session_id), session_context)

        logger.info(f"Created session {session_id} for {channel_type}")

        return {
            "session_id": session_id,
            "channel_type": channel_type,
            "started_at": started_at,
            "flow_id": flow_id
        }

    async def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session context from Redis

        Args:
            session_id: UUID string of the session

        Returns:
            Session context dictionary or None if not found
        """
        return await self.redis.get_session(session_id)

    async def update_session_context(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update session context in Redis

        Args:
            session_id: UUID string of the session
            updates: Dictionary of fields to update

        Returns:
            True if successful
        """
        context = await self.redis.get_session(session_id)
        if not context:
            logger.warning(f"Session {session_id} not found in Redis")
            return False

        # Special handling for slots - merge instead of replace
        if "slots" in updates:
            current_slots = context.get("slots", {})
            current_slots.update(updates["slots"])
            updates["slots"] = current_slots

        # Update context
        context.update(updates)

        # Save back to Redis
        return await self.redis.set_session(session_id, context)

    async def log_conversation_turn(
        self,
        session_id: uuid.UUID,
        turn_number: int,
        speaker: str,
        user_input_text: Optional[str] = None,
        detected_intent: Optional[str] = None,
        intent_confidence: Optional[float] = None,
        extracted_entities: Optional[list] = None,
        bot_response_text: Optional[str] = None,
        bot_action: Optional[str] = None
    ):
        """
        Log a conversation turn to the database

        Args:
            session_id: Session UUID
            turn_number: Sequential turn number
            speaker: 'user', 'bot', or 'agent'
            user_input_text: Text from user
            detected_intent: NLU detected intent
            intent_confidence: Confidence score
            extracted_entities: List of entities
            bot_response_text: Bot's response
            bot_action: Action taken
        """
        await self.db.execute(
            text("""
            INSERT INTO conversation_turns (
                session_id, turn_number, speaker,
                user_input_text, detected_intent, intent_confidence,
                extracted_entities, bot_response_text, bot_action,
                timestamp
            ) VALUES (
                :session_id, :turn_number, :speaker,
                :user_input_text, :detected_intent, :intent_confidence,
                CAST(:extracted_entities AS jsonb), :bot_response_text, :bot_action,
                NOW()
            )
            """),
            {
                "session_id": session_id,
                "turn_number": turn_number,
                "speaker": speaker,
                "user_input_text": user_input_text,
                "detected_intent": detected_intent,
                "intent_confidence": intent_confidence,
                "extracted_entities": json.dumps(extracted_entities or []),
                "bot_response_text": bot_response_text,
                "bot_action": bot_action
            }
        )
        await self.db.commit()

    async def end_session(
        self,
        session_id: uuid.UUID,
        reason: str,
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        End a conversation session

        Args:
            session_id: Session UUID
            reason: Reason for ending (completed, abandoned, etc.)
            user_feedback: Optional user feedback

        Returns:
            Session summary
        """
        # Get session data
        result = await self.db.execute(
            text("SELECT started_at FROM sessions WHERE session_id = :session_id"),
            {"session_id": session_id}
        )
        row = result.fetchone()
        if not row:
            raise ValueError(f"Session {session_id} not found")

        # Update session
        await self.db.execute(
            text("""
            UPDATE sessions
            SET ended_at = NOW(),
                current_state = :reason
            WHERE session_id = :session_id
            """),
            {"session_id": session_id, "reason": reason}
        )

        # Get turn count
        result = await self.db.execute(
            text("SELECT COUNT(*) FROM conversation_turns WHERE session_id = :session_id"),
            {"session_id": session_id}
        )
        turn_count = result.scalar()

        # Calculate duration
        result = await self.db.execute(
            text("SELECT duration_seconds FROM sessions WHERE session_id = :session_id"),
            {"session_id": session_id}
        )
        duration_seconds = result.scalar()

        await self.db.commit()

        return {
            "session_id": session_id,
            "duration_seconds": duration_seconds or 0,
            "turn_count": turn_count or 0,
            "reason": reason
        }
