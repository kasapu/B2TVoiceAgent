"""
Voice Connector Service - Main Application
WebSocket-based voice call handling
"""
import time
import asyncio
from typing import Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.services.call_manager import VoiceCallManager
from app.models.schemas import HealthResponse

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.VERSION,
    description="WebSocket-based voice connector for OCP Platform",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
active_calls: Dict[str, VoiceCallManager] = {}
start_time = time.time()


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.VERSION}")
    logger.info(f"STT Service: {settings.STT_SERVICE_URL}")
    logger.info(f"TTS Service: {settings.TTS_SERVICE_URL}")
    logger.info(f"Orchestrator: {settings.ORCHESTRATOR_URL}")
    logger.info(f"Max concurrent calls: {settings.MAX_CONCURRENT_CALLS}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Shutting down Voice Connector")

    # Stop all active calls
    if active_calls:
        logger.info(f"Stopping {len(active_calls)} active calls")
        for call_id, call_manager in list(active_calls.items()):
            try:
                await call_manager.stop()
            except Exception as e:
                logger.error(f"Error stopping call {call_id}: {e}")

    logger.info("Shutdown complete")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    uptime = int(time.time() - start_time)

    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        active_calls=len(active_calls),
        uptime_seconds=uptime,
        stt_service=settings.STT_SERVICE_URL,
        tts_service=settings.TTS_SERVICE_URL,
        orchestrator_service=settings.ORCHESTRATOR_URL,
    )


@app.get("/calls")
async def get_active_calls():
    """Get active calls"""
    calls = []
    for call_id, call_manager in active_calls.items():
        call_info = call_manager.get_call_info()
        calls.append({
            "call_id": call_info.call_id,
            "session_id": call_info.session_id,
            "state": call_info.state,
            "turns_count": call_info.turns_count,
        })

    return {
        "active_calls": len(calls),
        "max_calls": settings.MAX_CONCURRENT_CALLS,
        "calls": calls,
    }


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for voice calls

    Protocol:
    - Client connects and sends audio chunks (binary frames)
    - Server processes audio: STT -> Orchestrator -> TTS
    - Server sends back audio responses (binary frames)
    - Heartbeat messages sent periodically (JSON frames)
    """
    call_manager: Optional[VoiceCallManager] = None

    try:
        # Accept connection
        await websocket.accept()
        logger.info("WebSocket connection accepted")

        # Check concurrent call limit
        if len(active_calls) >= settings.MAX_CONCURRENT_CALLS:
            logger.warning(
                f"Max concurrent calls reached ({settings.MAX_CONCURRENT_CALLS})"
            )
            await websocket.close(code=1008, reason="Max concurrent calls reached")
            return

        # Create call manager
        call_manager = VoiceCallManager(websocket=websocket)
        call_id = call_manager.call_id

        # Add to active calls
        active_calls[call_id] = call_manager

        logger.info(
            f"New call {call_id} "
            f"(active: {len(active_calls)}/{settings.MAX_CONCURRENT_CALLS})"
        )

        # Start call
        await call_manager.start()

        # Send initial status
        await websocket.send_json({
            "type": "status",
            "call_id": call_id,
            "session_id": call_manager.session_id,
            "state": "connected",
        })

        # Main message loop
        while True:
            # Receive message
            try:
                # Try to receive binary data (audio)
                data = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=settings.WS_TIMEOUT,
                )

                # Handle different message types
                if "bytes" in data:
                    # Audio chunk
                    audio_data = data["bytes"]
                    await call_manager.handle_audio_chunk(audio_data)

                elif "text" in data:
                    # Control message (JSON)
                    import json
                    message = json.loads(data["text"])
                    message_type = message.get("type")

                    if message_type == "ping":
                        await websocket.send_json({"type": "pong"})

                    elif message_type == "end_call":
                        logger.info(f"Client requested call end (call: {call_id})")
                        break

                    else:
                        logger.warning(f"Unknown message type: {message_type}")

            except asyncio.TimeoutError:
                logger.warning(f"WebSocket timeout (call: {call_id})")
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected (call: {call_manager.call_id if call_manager else 'unknown'})")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")
        except:
            pass

    finally:
        # Cleanup
        if call_manager:
            call_id = call_manager.call_id

            try:
                # Stop call manager
                await call_manager.stop()

                # Remove from active calls
                if call_id in active_calls:
                    del active_calls[call_id]

                logger.info(
                    f"Call {call_id} ended "
                    f"(remaining: {len(active_calls)}, "
                    f"turns: {call_manager.call_info.turns_count})"
                )

            except Exception as e:
                logger.error(f"Error during call cleanup: {e}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "websocket": "/ws/voice",
            "calls": "/calls",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=True,
    )
