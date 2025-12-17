"""
OCP Platform - Chat Connector Service
WebSocket service for real-time chat conversations
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set
import httpx
import logging
import json
import uuid
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OCP Chat Connector",
    description="WebSocket service for chat conversations",
    version="1.0.0"
)

# CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")

# Active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


# ============================================
# CONNECTION MANAGER
# ============================================

class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")

    async def send_message(self, session_id: str, message: dict):
        """Send message to specific connection"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)


manager = ConnectionManager()


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OCP Chat Connector",
        "version": "1.0.0",
        "active_connections": manager.get_connection_count()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_connections": manager.get_connection_count()
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for chat

    Protocol:
    1. Client connects
    2. Server creates session and sends session_id
    3. Client sends messages as: {"type": "message", "text": "..."}
    4. Server forwards to orchestrator and returns response
    5. Client can end with: {"type": "end"}
    """
    session_id = None

    try:
        # Accept connection
        await websocket.accept()
        logger.info("New WebSocket connection established")

        # Create session with orchestrator
        session_id = await create_session()

        # Store connection
        manager.active_connections[session_id] = websocket

        # Send session info to client
        await websocket.send_json({
            "type": "session_created",
            "session_id": session_id,
            "message": "Connected to OCP Platform"
        })

        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")

            logger.info(f"Session {session_id}: Received {message_type}")

            if message_type == "message":
                # Process user message
                user_text = data.get("text", "")

                if not user_text.strip():
                    await websocket.send_json({
                        "type": "error",
                        "message": "Empty message"
                    })
                    continue

                # Send typing indicator
                await websocket.send_json({
                    "type": "typing",
                    "is_typing": True
                })

                # Forward to orchestrator
                response = await process_message(session_id, user_text)

                # Send response back to client
                await websocket.send_json({
                    "type": "message",
                    "speaker": "bot",
                    "text": response["text"],
                    "intent": response.get("intent"),
                    "confidence": response.get("confidence"),
                    "turn_number": response.get("turn_number")
                })

                # Check if conversation should end
                if response.get("next_action") == "end_conversation":
                    await websocket.send_json({
                        "type": "conversation_ended",
                        "message": "Thank you for using OCP Platform!"
                    })
                    break

            elif message_type == "end":
                # Client wants to end conversation
                await end_session(session_id, "user_initiated")

                await websocket.send_json({
                    "type": "session_ended",
                    "message": "Goodbye!"
                })
                break

            elif message_type == "ping":
                # Keep-alive ping
                await websocket.send_json({
                    "type": "pong"
                })

            else:
                # Unknown message type
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": "An error occurred"
            })
        except:
            pass

    finally:
        # Cleanup
        if session_id:
            manager.disconnect(session_id)
            try:
                await end_session(session_id, "disconnected")
            except:
                pass


# ============================================
# ORCHESTRATOR CLIENT
# ============================================

async def create_session() -> str:
    """
    Create new session with orchestrator

    Returns:
        Session ID
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/v1/conversations/start",
                json={
                    "channel_type": "chat"
                },
                timeout=10.0
            )

            if response.status_code == 201:
                data = response.json()
                session_id = data["session_id"]
                logger.info(f"Created session: {session_id}")
                return session_id
            else:
                logger.error(f"Failed to create session: {response.status_code}")
                # Return fallback session ID
                return str(uuid.uuid4())

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        # Return fallback session ID
        return str(uuid.uuid4())


async def process_message(session_id: str, text: str) -> Dict:
    """
    Process user message through orchestrator

    Args:
        session_id: Session UUID
        text: User message text

    Returns:
        Dict with bot response
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/v1/conversations/{session_id}/process",
                json={
                    "input_type": "text",
                    "text": text
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()

                return {
                    "text": data["response"]["text"],
                    "intent": data["nlu"]["intent"]["name"],
                    "confidence": data["nlu"]["intent"]["confidence"],
                    "turn_number": data["turn_number"],
                    "next_action": data["next_action"]["action_type"]
                }
            else:
                logger.error(f"Orchestrator error: {response.status_code} - {response.text}")
                return {
                    "text": "I'm having trouble understanding. Could you please try again?",
                    "intent": "error",
                    "confidence": 0.0,
                    "turn_number": 0,
                    "next_action": "wait_for_input"
                }

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return {
            "text": "I'm sorry, I encountered an error. Please try again.",
            "intent": "error",
            "confidence": 0.0,
            "turn_number": 0,
            "next_action": "wait_for_input"
        }


async def end_session(session_id: str, reason: str):
    """
    End session with orchestrator

    Args:
        session_id: Session UUID
        reason: Reason for ending
    """
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{ORCHESTRATOR_URL}/v1/conversations/{session_id}/end",
                json={
                    "reason": reason
                },
                timeout=5.0
            )
            logger.info(f"Ended session: {session_id}")

    except Exception as e:
        logger.error(f"Error ending session: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=True
    )
