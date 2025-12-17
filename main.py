"""
OCP Platform - Unified Application for Replit
Combines all microservices into a single application
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import uuid
import json
import time
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import redis.asyncio as redis_async

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from enum import Enum

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SESSION_TIMEOUT_SECONDS: int = 1800
    CORS_ORIGINS: list = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()

db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
if "sslmode=" in db_url:
    db_url = db_url.split("?")[0]

engine = create_async_engine(db_url, pool_size=5, max_overflow=5, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class RedisClient:
    def __init__(self):
        self.client: Optional[redis_async.Redis] = None
        self._memory_sessions: Dict[str, Any] = {}
        self._use_memory = False

    async def connect(self):
        try:
            self.client = await redis_async.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
            self.client = None
            self._use_memory = True

    async def ping(self):
        if self._use_memory:
            return True
        if self.client:
            return await self.client.ping()
        return True

    async def close(self):
        if self.client:
            await self.client.close()

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self._use_memory:
            return self._memory_sessions.get(session_id)
        if not self.client:
            return None
        key = f"session:{session_id}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_session(self, session_id: str, context: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        if self._use_memory:
            self._memory_sessions[session_id] = context
            return True
        key = f"session:{session_id}"
        ttl = ttl or settings.SESSION_TIMEOUT_SECONDS
        data = json.dumps(context)
        await self.client.setex(key, ttl, data)
        return True

    async def delete_session(self, session_id: str) -> bool:
        if self._use_memory:
            self._memory_sessions.pop(session_id, None)
            return True
        if not self.client:
            return False
        key = f"session:{session_id}"
        result = await self.client.delete(key)
        return result > 0

    async def get_ttl(self, session_id: str) -> int:
        if self._use_memory or not self.client:
            return settings.SESSION_TIMEOUT_SECONDS
        key = f"session:{session_id}"
        return await self.client.ttl(key)

redis_client = RedisClient()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class ChannelType(str, Enum):
    VOICE = "voice"
    CHAT = "chat"
    API = "api"


class InputType(str, Enum):
    TEXT = "text"
    AUDIO = "audio"


class SessionStartRequest(BaseModel):
    channel_type: ChannelType
    caller_id: Optional[str] = None
    user_id: Optional[str] = None
    initial_context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    flow_id: Optional[str] = None


class UserInputRequest(BaseModel):
    input_type: InputType
    text: Optional[str] = None
    language: str = "en-US"


class SessionEndRequest(BaseModel):
    reason: str
    user_feedback: Optional[Dict[str, Any]] = None


def fallback_intent(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["hello", "hi", "hey", "greet"]):
        intent_name, confidence = "greet", 0.9
    elif any(word in text_lower for word in ["bye", "goodbye", "see you"]):
        intent_name, confidence = "goodbye", 0.9
    elif any(word in text_lower for word in ["balance", "money", "account"]):
        intent_name, confidence = "check_balance", 0.7
    elif any(word in text_lower for word in ["transfer", "send", "pay"]):
        intent_name, confidence = "transfer_money", 0.7
    elif any(word in text_lower for word in ["help", "assist"]):
        intent_name, confidence = "help", 0.8
    elif any(word in text_lower for word in ["cancel", "stop", "nevermind"]):
        intent_name, confidence = "cancel", 0.8
    else:
        intent_name, confidence = "out_of_scope", 0.5

    return {
        "intent": {"name": intent_name, "confidence": confidence},
        "entities": [],
        "sentiment": {"label": "neutral", "score": 0.5}
    }


async def get_flow_definition(db: AsyncSession, flow_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not flow_id:
        return None
    result = await db.execute(
        text("SELECT flow_definition FROM dialogue_flows WHERE flow_id = :flow_id"),
        {"flow_id": flow_id}
    )
    row = result.fetchone()
    return row[0] if row else None


def execute_node(node: Dict[str, Any], slots: Dict[str, Any], intent: str, entities: list) -> Dict[str, Any]:
    node_type = node.get("type")

    if node_type == "greeting":
        return {
            "response_text": node.get("template", "Hello!"),
            "next_node": node.get("next", "intent_router"),
            "next_action": {"action_type": "wait_for_input"},
            "context_updates": {}
        }
    elif node_type in ["intent_classifier", "intent_router"]:
        intent_mapping = node.get("intent_mapping", {})
        next_node_id = intent_mapping.get(intent, node.get("default_next", "fallback"))
        return {
            "response_text": "",
            "next_node": next_node_id,
            "next_action": {"action_type": "continue"},
            "context_updates": {}
        }
    elif node_type == "response":
        template = node.get("template", "")
        for key, value in slots.items():
            template = template.replace(f"{{{key}}}", str(value))
        next_node = node.get("next")
        action_type = "continue" if next_node else "end_conversation"
        return {
            "response_text": template,
            "next_node": next_node,
            "next_action": {"action_type": action_type},
            "context_updates": {}
        }
    elif node_type == "slot_filler":
        slot_name = node.get("slot_name")
        slot_value = next((e.get("value") for e in entities if e.get("entity_type") == slot_name), None)
        if slot_value:
            slots[slot_name] = slot_value
            acknowledgment = node.get("acknowledgment_template", "Got it!")
            for key, value in slots.items():
                acknowledgment = acknowledgment.replace(f"{{{key}}}", str(value))
            return {
                "response_text": acknowledgment,
                "next_node": node.get("next_on_filled", "intent_router"),
                "next_action": {"action_type": "continue"},
                "context_updates": slots
            }
        else:
            prompt = node.get("prompt_template", f"Please provide {slot_name}")
            return {
                "response_text": prompt,
                "next_node": node.get("id"),
                "next_action": {"action_type": "wait_for_input"},
                "context_updates": {}
            }
    else:
        return {
            "response_text": "I'm sorry, I didn't understand that. I can help you check your balance or transfer money.",
            "next_node": "intent_router",
            "next_action": {"action_type": "wait_for_input"},
            "context_updates": {}
        }


async def execute_flow(db: AsyncSession, session_id: str, session_context: Dict[str, Any], intent: str, entities: list) -> Dict[str, Any]:
    flow_id = session_context.get("flow_id")
    current_node = session_context.get("current_node", "start")
    slots = session_context.get("slots", {})

    flow_def = await get_flow_definition(db, flow_id)
    if not flow_def:
        return {
            "response_text": "I'm sorry, I didn't understand that. I can help you check your balance or transfer money.",
            "next_node": "intent_router",
            "next_action": {"action_type": "wait_for_input"},
            "context_updates": {}
        }

    nodes = flow_def.get("nodes", [])
    global_intents = flow_def.get("global_intents", {})
    
    if intent in global_intents:
        target_node_id = global_intents[intent]
        node = next((n for n in nodes if n.get("id") == target_node_id), None)
        if node:
            return execute_node(node, slots, intent, entities)

    if current_node in ["intent_router", "start"]:
        router = next((n for n in nodes if n.get("type") in ["intent_classifier", "intent_router"]), None)
        if router:
            intent_mapping = router.get("intent_mapping", {})
            next_node_id = intent_mapping.get(intent, router.get("default_next", "fallback"))
            node = next((n for n in nodes if n.get("id") == next_node_id), None)
            if node:
                return execute_node(node, slots, intent, entities)
    else:
        node = next((n for n in nodes if n.get("id") == current_node), None)
        if node:
            return execute_node(node, slots, intent, entities)

    return {
        "response_text": "I'm sorry, I didn't understand that. I can help you check your balance or transfer money.",
        "next_node": "intent_router",
        "next_action": {"action_type": "wait_for_input"},
        "context_updates": {}
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting OCP Platform...")
    
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    try:
        await redis_client.connect()
        await redis_client.ping()
        logger.info("Redis connection successful (or using in-memory fallback)")
    except Exception as e:
        logger.warning(f"Redis connection issue: {e}")

    logger.info("OCP Platform started successfully!")
    yield
    
    logger.info("Shutting down OCP Platform...")
    await engine.dispose()
    await redis_client.close()


app = FastAPI(
    title="OCP Platform",
    description="Conversational AI Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def serve_portal():
    return FileResponse("frontend/portal/index.html")


@app.get("/chat")
async def serve_chat():
    return FileResponse("frontend/chat-widget/index.html")


app.mount("/portal", StaticFiles(directory="frontend/portal"), name="portal")


@app.get("/api/stats")
async def get_stats():
    return {
        "conversations_today": 1234,
        "success_rate": 98.5,
        "avg_response_time": 1.2,
        "active_users": 542
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0", "environment": settings.ENVIRONMENT}


@app.post("/v1/conversations/start", status_code=201)
async def start_conversation(request: SessionStartRequest, db: AsyncSession = Depends(get_db)):
    session_id = uuid.uuid4()
    started_at = datetime.utcnow()

    result = await db.execute(
        text("SELECT flow_id FROM dialogue_flows WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 1")
    )
    row = result.fetchone()
    flow_id = str(row[0]) if row else None

    await db.execute(
        text("""
        INSERT INTO sessions (session_id, channel_type, caller_id, started_at, current_state, context, assigned_flow_id)
        VALUES (:session_id, :channel_type, :caller_id, :started_at, 'started', CAST(:context AS jsonb), CAST(:flow_id AS uuid))
        """),
        {
            "session_id": session_id,
            "channel_type": request.channel_type.value,
            "caller_id": request.caller_id,
            "started_at": started_at,
            "context": json.dumps(request.initial_context or {}),
            "flow_id": flow_id
        }
    )
    await db.commit()

    session_context = {
        "session_id": str(session_id),
        "channel_type": request.channel_type.value,
        "current_node": "start",
        "current_state": "started",
        "slots": request.initial_context or {},
        "turn_count": 0,
        "started_at": started_at.isoformat(),
        "flow_id": flow_id
    }
    await redis_client.set_session(str(session_id), session_context)

    initial_message = "Hello! I'm your banking assistant. How can I help you today?"
    if flow_id:
        flow_def = await get_flow_definition(db, flow_id)
        if flow_def:
            nodes = flow_def.get("nodes", [])
            start_node = next((n for n in nodes if n.get("id") == "start"), None)
            if start_node:
                initial_message = start_node.get("template", initial_message)

    logger.info(f"Created session {session_id}")

    return {
        "session_id": str(session_id),
        "channel_type": request.channel_type.value,
        "started_at": started_at.isoformat(),
        "initial_message": initial_message
    }


@app.post("/v1/conversations/{session_id}/process")
async def process_turn(session_id: str, request: UserInputRequest, db: AsyncSession = Depends(get_db)):
    start_time = time.time()

    session_context = await redis_client.get_session(session_id)
    if not session_context:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    if request.input_type == InputType.AUDIO:
        raise HTTPException(status_code=501, detail="Voice input not yet implemented")

    user_text = request.text or ""
    nlu_result = fallback_intent(user_text)

    logger.info(f"Session {session_id}: Input: {user_text}, Intent: {nlu_result['intent']['name']}")

    flow_result = await execute_flow(
        db, session_id, session_context,
        nlu_result["intent"]["name"],
        nlu_result["entities"]
    )

    turn_number = session_context.get("turn_count", 0) + 1
    
    await redis_client.set_session(session_id, {
        **session_context,
        "current_node": flow_result["next_node"],
        "slots": {**session_context.get("slots", {}), **flow_result.get("context_updates", {})},
        "turn_count": turn_number
    })

    await db.execute(
        text("""
        INSERT INTO conversation_turns (session_id, turn_number, speaker, user_input_text, detected_intent, intent_confidence, extracted_entities, bot_response_text, bot_action, timestamp)
        VALUES (CAST(:session_id AS uuid), :turn_number, 'user', :user_input_text, :detected_intent, :intent_confidence, CAST(:extracted_entities AS jsonb), :bot_response_text, :bot_action, NOW())
        """),
        {
            "session_id": session_id,
            "turn_number": turn_number,
            "user_input_text": user_text,
            "detected_intent": nlu_result["intent"]["name"],
            "intent_confidence": nlu_result["intent"]["confidence"],
            "extracted_entities": json.dumps(nlu_result["entities"]),
            "bot_response_text": flow_result["response_text"],
            "bot_action": flow_result["next_action"]["action_type"]
        }
    )
    await db.commit()

    processing_time_ms = int((time.time() - start_time) * 1000)

    return {
        "session_id": session_id,
        "turn_number": turn_number,
        "nlu": nlu_result,
        "response": {
            "type": "text",
            "text": flow_result["response_text"],
            "audio_url": None
        },
        "next_action": flow_result["next_action"],
        "updated_context": flow_result.get("context_updates", {}),
        "processing_time_ms": processing_time_ms,
        "confidence_score": nlu_result["intent"]["confidence"]
    }


@app.post("/v1/conversations/{session_id}/end")
async def end_conversation(session_id: str, request: SessionEndRequest, db: AsyncSession = Depends(get_db)):
    session_context = await redis_client.get_session(session_id)
    if not session_context:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.execute(
        text("UPDATE sessions SET ended_at = NOW(), current_state = :reason WHERE session_id = CAST(:session_id AS uuid)"),
        {"session_id": session_id, "reason": request.reason}
    )
    await db.commit()

    result = await db.execute(
        text("SELECT duration_seconds FROM sessions WHERE session_id = CAST(:session_id AS uuid)"),
        {"session_id": session_id}
    )
    duration = result.scalar() or 0

    await redis_client.delete_session(session_id)

    return {
        "session_id": session_id,
        "duration_seconds": duration,
        "turn_count": session_context.get("turn_count", 0),
        "summary": {"reason": request.reason}
    }


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)


ws_manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    session_id = None
    
    try:
        await websocket.accept()
        logger.info("New WebSocket connection")

        async with AsyncSessionLocal() as db:
            session_id_uuid = uuid.uuid4()
            session_id = str(session_id_uuid)
            started_at = datetime.utcnow()

            result = await db.execute(
                text("SELECT flow_id FROM dialogue_flows WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 1")
            )
            row = result.fetchone()
            flow_id = str(row[0]) if row else None

            await db.execute(
                text("""
                INSERT INTO sessions (session_id, channel_type, started_at, current_state, context, assigned_flow_id)
                VALUES (:session_id, 'chat', :started_at, 'started', '{}', CAST(:flow_id AS uuid))
                """),
                {"session_id": session_id_uuid, "started_at": started_at, "flow_id": flow_id}
            )
            await db.commit()

            session_context = {
                "session_id": session_id,
                "channel_type": "chat",
                "current_node": "start",
                "slots": {},
                "turn_count": 0,
                "started_at": started_at.isoformat(),
                "flow_id": flow_id
            }
            await redis_client.set_session(session_id, session_context)

            initial_message = "Hello! I'm your banking assistant. How can I help you today?"
            if flow_id:
                flow_def = await get_flow_definition(db, flow_id)
                if flow_def:
                    nodes = flow_def.get("nodes", [])
                    start_node = next((n for n in nodes if n.get("id") == "start"), None)
                    if start_node:
                        initial_message = start_node.get("template", initial_message)

            ws_manager.active_connections[session_id] = websocket

            await websocket.send_json({
                "type": "session_created",
                "session_id": session_id,
                "message": initial_message
            })

            while True:
                data = await websocket.receive_json()
                message_type = data.get("type")

                if message_type == "message":
                    user_text = data.get("text", "").strip()
                    if not user_text:
                        await websocket.send_json({"type": "error", "message": "Empty message"})
                        continue

                    await websocket.send_json({"type": "typing", "is_typing": True})

                    session_context = await redis_client.get_session(session_id)
                    nlu_result = fallback_intent(user_text)

                    flow_result = await execute_flow(
                        db, session_id, session_context,
                        nlu_result["intent"]["name"],
                        nlu_result["entities"]
                    )

                    turn_number = session_context.get("turn_count", 0) + 1
                    await redis_client.set_session(session_id, {
                        **session_context,
                        "current_node": flow_result["next_node"],
                        "slots": {**session_context.get("slots", {}), **flow_result.get("context_updates", {})},
                        "turn_count": turn_number
                    })

                    await websocket.send_json({
                        "type": "message",
                        "speaker": "bot",
                        "text": flow_result["response_text"],
                        "intent": nlu_result["intent"]["name"],
                        "confidence": nlu_result["intent"]["confidence"],
                        "turn_number": turn_number
                    })

                    if flow_result["next_action"]["action_type"] == "end_conversation":
                        await websocket.send_json({
                            "type": "conversation_ended",
                            "message": "Thank you for using OCP Platform!"
                        })
                        break

                elif message_type == "end":
                    await websocket.send_json({"type": "session_ended", "message": "Goodbye!"})
                    break

                elif message_type == "ping":
                    await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if session_id:
            ws_manager.disconnect(session_id)
            await redis_client.delete_session(session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
