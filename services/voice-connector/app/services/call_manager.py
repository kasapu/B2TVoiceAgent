"""
Voice Call Manager
Orchestrates voice call flow: WebSocket -> STT -> Orchestrator -> TTS -> WebSocket
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import WebSocket
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.schemas import CallState, CallInfo, MessageType
from app.services.audio_buffer import AudioBuffer
from app.services.stt_client import STTClient
from app.services.tts_client import TTSClient
from app.services.orchestrator_client import OrchestratorClient

logger = get_logger(__name__)


class VoiceCallManager:
    """
    Manages a single voice call session
    Handles the complete flow: Audio -> STT -> Orchestrator -> TTS -> Audio
    """

    def __init__(
        self,
        websocket: WebSocket,
        call_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """
        Initialize call manager

        Args:
            websocket: WebSocket connection
            call_id: Unique call ID (generated if not provided)
            session_id: Conversation session ID (created if not provided)
        """
        self.websocket = websocket
        self.call_id = call_id or str(uuid.uuid4())
        self.session_id = session_id
        self.state = CallState.CONNECTING

        # Service clients
        self.stt_client = STTClient()
        self.tts_client = TTSClient()
        self.orchestrator_client = OrchestratorClient()

        # Audio buffer
        self.audio_buffer = AudioBuffer(
            sample_rate=settings.SAMPLE_RATE,
            chunk_size=settings.CHUNK_SIZE,
            buffer_duration_ms=settings.BUFFER_DURATION_MS,
            silence_threshold=settings.SILENCE_THRESHOLD,
            silence_duration_ms=settings.SILENCE_DURATION_MS,
        )

        # Call info
        self.call_info = CallInfo(
            call_id=self.call_id,
            session_id=self.session_id or "",
            state=self.state,
            turns_count=0,
        )

        # Tasks
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.running = False

        logger.info(f"VoiceCallManager created (call_id: {self.call_id})")

    async def start(self) -> None:
        """Start the call manager"""
        try:
            logger.info(f"Starting call {self.call_id}")

            # Start service clients
            await self.stt_client.start()
            await self.tts_client.start()
            await self.orchestrator_client.start()

            # Create session if not provided
            if not self.session_id:
                self.session_id = await self.orchestrator_client.create_session(
                    channel="voice"
                )
                if not self.session_id:
                    raise Exception("Failed to create conversation session")

                self.call_info.session_id = self.session_id
                logger.info(f"Created session {self.session_id} for call {self.call_id}")

            # Update state
            self.state = CallState.CONNECTED
            self.call_info.state = self.state
            self.call_info.connected_at = datetime.utcnow()
            self.running = True

            # Start heartbeat
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # Send welcome message
            await self._send_welcome()

            logger.info(f"Call {self.call_id} started successfully")

        except Exception as e:
            logger.error(f"Error starting call {self.call_id}: {e}")
            self.state = CallState.ERROR
            self.call_info.state = self.state
            self.call_info.error = str(e)
            raise

    async def stop(self) -> None:
        """Stop the call manager"""
        logger.info(f"Stopping call {self.call_id}")

        self.running = False
        self.state = CallState.DISCONNECTED
        self.call_info.state = self.state
        self.call_info.disconnected_at = datetime.utcnow()

        # Calculate duration
        if self.call_info.connected_at and self.call_info.disconnected_at:
            duration = (
                self.call_info.disconnected_at - self.call_info.connected_at
            ).total_seconds()
            self.call_info.duration_seconds = int(duration)

        # Cancel heartbeat
        if self.heartbeat_task:
            self.heartbeat_task.cancel()

        # Stop service clients
        await self.stt_client.stop()
        await self.tts_client.stop()
        await self.orchestrator_client.stop()

        logger.info(
            f"Call {self.call_id} stopped "
            f"(duration: {self.call_info.duration_seconds}s, "
            f"turns: {self.call_info.turns_count})"
        )

    async def handle_audio_chunk(self, audio_data: bytes) -> None:
        """
        Handle incoming audio chunk

        Args:
            audio_data: Raw audio bytes
        """
        try:
            # Update state
            if self.state != CallState.LISTENING:
                self.state = CallState.LISTENING
                logger.debug(f"Call {self.call_id} now listening")

            # Add to buffer
            self.audio_buffer.add_chunk(audio_data)

            # Check if should process
            if self.audio_buffer.should_flush():
                await self._process_buffered_audio()

        except Exception as e:
            logger.error(f"Error handling audio chunk: {e}")

    async def _process_buffered_audio(self) -> None:
        """Process buffered audio through STT -> Orchestrator -> TTS"""
        try:
            # Get audio from buffer
            audio_data = self.audio_buffer.get_audio()
            if not audio_data:
                logger.warning("No audio data in buffer")
                return

            logger.info(
                f"Processing buffered audio "
                f"(call: {self.call_id}, size: {len(audio_data)} bytes)"
            )

            # Clear buffer
            self.audio_buffer.clear()

            # Update state
            self.state = CallState.PROCESSING

            # 1. Transcribe audio (STT)
            transcription = await self.stt_client.transcribe(
                audio_data=audio_data,
                language="en",
                session_id=self.session_id,
            )

            if not transcription or not transcription.text.strip():
                logger.warning(f"Empty transcription (call: {self.call_id})")
                self.state = CallState.LISTENING
                return

            logger.info(
                f"Transcribed: '{transcription.text}' (call: {self.call_id})"
            )

            # 2. Get response from orchestrator
            conversation_response = await self.orchestrator_client.send_message(
                session_id=self.session_id,
                user_message=transcription.text,
                channel="voice",
                metadata={"call_id": self.call_id},
            )

            if not conversation_response or not conversation_response.response.strip():
                logger.warning(f"Empty orchestrator response (call: {self.call_id})")
                self.state = CallState.LISTENING
                return

            logger.info(
                f"Got response: '{conversation_response.response}' "
                f"(call: {self.call_id}, intent: {conversation_response.intent})"
            )

            # 3. Synthesize response (TTS)
            self.state = CallState.SPEAKING

            synthesis = await self.tts_client.synthesize(
                text=conversation_response.response,
                voice="default",
                speed=1.0,
                session_id=self.session_id,
            )

            if not synthesis or not synthesis.audio_url:
                logger.warning(f"Failed to synthesize audio (call: {self.call_id})")
                self.state = CallState.LISTENING
                return

            logger.info(
                f"Synthesized audio URL: {synthesis.audio_url} "
                f"(call: {self.call_id})"
            )

            # 4. Download audio
            audio_bytes = await self.tts_client.download_audio(synthesis.audio_url)

            if not audio_bytes:
                logger.warning(f"Failed to download audio (call: {self.call_id})")
                self.state = CallState.LISTENING
                return

            # 5. Send audio to caller
            await self._send_audio(audio_bytes)

            # Update turn count
            self.call_info.turns_count += 1

            # Back to listening
            self.state = CallState.LISTENING

            logger.info(
                f"Turn {self.call_info.turns_count} completed "
                f"(call: {self.call_id})"
            )

        except Exception as e:
            logger.error(f"Error processing buffered audio: {e}")
            self.state = CallState.ERROR
            self.call_info.error = str(e)

    async def _send_audio(self, audio_data: bytes) -> None:
        """
        Send audio to WebSocket

        Args:
            audio_data: Audio bytes to send
        """
        try:
            await self.websocket.send_bytes(audio_data)
            logger.debug(f"Sent {len(audio_data)} bytes of audio")
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            raise

    async def _send_welcome(self) -> None:
        """Send welcome message"""
        try:
            welcome_text = "Hello! I'm your voice assistant. How can I help you today?"

            synthesis = await self.tts_client.synthesize(
                text=welcome_text,
                voice="default",
                speed=1.0,
                session_id=self.session_id,
            )

            if synthesis and synthesis.audio_url:
                audio_bytes = await self.tts_client.download_audio(synthesis.audio_url)
                if audio_bytes:
                    await self._send_audio(audio_bytes)
                    logger.info(f"Sent welcome message (call: {self.call_id})")

        except Exception as e:
            logger.error(f"Error sending welcome: {e}")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats"""
        try:
            while self.running:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                await self.websocket.send_json({"type": "heartbeat"})
                logger.debug(f"Sent heartbeat (call: {self.call_id})")
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat cancelled (call: {self.call_id})")
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

    def get_call_info(self) -> CallInfo:
        """Get current call info"""
        return self.call_info
