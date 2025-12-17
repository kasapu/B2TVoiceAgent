"""
SIP Call Bridge
Bridges SIP calls (via FreeSWITCH) to Voice Connector (WebSocket)
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.schemas import SIPCallInfo, CallState
from app.services.audio_converter import AudioConverter
from app.services.voice_connector_client import VoiceConnectorClient
from app.services.esl_handler import ESLHandler

logger = get_logger(__name__)


class SIPCallBridge:
    """
    Bridges a SIP call to the Voice Connector platform

    This class:
    - Manages the lifecycle of a single SIP call
    - Handles bidirectional audio streaming
    - Converts audio formats (G.711 μ-law 8kHz <-> PCM 16kHz)
    - Coordinates FreeSWITCH and Voice Connector
    """

    def __init__(
        self,
        sip_call_id: str,
        unique_id: str,
        caller_number: str,
        callee_number: str,
        esl_handler: ESLHandler
    ):
        """
        Initialize SIP call bridge

        Args:
            sip_call_id: SIP protocol call ID
            unique_id: FreeSWITCH unique call ID
            caller_number: Caller phone number
            callee_number: Called phone number
            esl_handler: Shared ESL handler instance
        """
        self.call_id = str(uuid.uuid4())
        self.sip_call_id = sip_call_id
        self.unique_id = unique_id
        self.caller_number = caller_number
        self.callee_number = callee_number

        # Services
        self.esl_handler = esl_handler
        self.voice_connector = VoiceConnectorClient()
        self.audio_converter = AudioConverter()

        # Call info
        self.call_info = SIPCallInfo(
            call_id=self.call_id,
            sip_call_id=self.sip_call_id,
            caller_number=self.caller_number,
            callee_number=self.callee_number,
            state=CallState.CONNECTING
        )

        # State
        self.state = CallState.CONNECTING
        self.is_running = False

        # Audio streaming tasks
        self.sip_to_ws_task: Optional[asyncio.Task] = None
        self.ws_to_sip_task: Optional[asyncio.Task] = None

        # Audio queues for buffering
        self.sip_audio_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.ws_audio_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

        logger.info(f"SIPCallBridge created (call_id: {self.call_id}, from: {caller_number})")

    async def start(self) -> bool:
        """
        Start bridging the call

        Returns:
            True if bridge started successfully
        """
        try:
            logger.info(f"Starting SIP call bridge {self.call_id}")

            # Connect to Voice Connector
            self.voice_connector.set_on_audio_callback(self._on_voice_connector_audio)
            self.voice_connector.set_on_message_callback(self._on_voice_connector_message)

            connected = await self.voice_connector.connect()
            if not connected:
                logger.error(f"Failed to connect to Voice Connector for call {self.call_id}")
                return False

            # Update state
            self.state = CallState.BRIDGED
            self.call_info.state = CallState.BRIDGED
            self.call_info.connected_at = datetime.utcnow()
            self.is_running = True

            # Start bidirectional audio streaming
            self.sip_to_ws_task = asyncio.create_task(self._stream_sip_to_websocket())
            self.ws_to_sip_task = asyncio.create_task(self._stream_websocket_to_sip())

            logger.info(f"SIP call bridge {self.call_id} started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start SIP call bridge: {str(e)}")
            await self.stop()
            return False

    async def stop(self) -> None:
        """Stop the bridge and cleanup resources"""
        logger.info(f"Stopping SIP call bridge {self.call_id}")

        self.is_running = False
        self.state = CallState.DISCONNECTING

        # Cancel streaming tasks
        if self.sip_to_ws_task and not self.sip_to_ws_task.done():
            self.sip_to_ws_task.cancel()
            try:
                await self.sip_to_ws_task
            except asyncio.CancelledError:
                pass

        if self.ws_to_sip_task and not self.ws_to_sip_task.done():
            self.ws_to_sip_task.cancel()
            try:
                await self.ws_to_sip_task
            except asyncio.CancelledError:
                pass

        # Disconnect Voice Connector
        await self.voice_connector.disconnect()

        # Update call info
        self.state = CallState.DISCONNECTED
        self.call_info.state = CallState.DISCONNECTED
        self.call_info.disconnected_at = datetime.utcnow()

        if self.call_info.connected_at:
            duration = (self.call_info.disconnected_at - self.call_info.connected_at).total_seconds()
            self.call_info.duration_seconds = duration

        logger.info(f"SIP call bridge {self.call_id} stopped (duration: {self.call_info.duration_seconds:.1f}s)")

    async def handle_sip_audio(self, audio_data: bytes) -> None:
        """
        Handle incoming audio from SIP (FreeSWITCH)

        Args:
            audio_data: G.711 μ-law audio at 8kHz
        """
        try:
            # Queue audio for processing
            await self.sip_audio_queue.put(audio_data)
        except asyncio.QueueFull:
            logger.warning(f"SIP audio queue full for call {self.call_id}, dropping packet")

    async def _stream_sip_to_websocket(self) -> None:
        """Stream audio from SIP to WebSocket (inbound)"""
        logger.info(f"Starting SIP → WebSocket audio stream for call {self.call_id}")

        try:
            while self.is_running:
                try:
                    # Get audio from queue (with timeout)
                    sip_audio = await asyncio.wait_for(
                        self.sip_audio_queue.get(),
                        timeout=1.0
                    )

                    # Convert: G.711 μ-law 8kHz → PCM 16kHz
                    platform_audio = self.audio_converter.convert_sip_to_platform(
                        sip_audio,
                        sip_sample_rate=settings.SIP_SAMPLE_RATE
                    )

                    # Send to Voice Connector
                    await self.voice_connector.send_audio(platform_audio)

                except asyncio.TimeoutError:
                    # No audio available, continue
                    continue
                except Exception as e:
                    logger.error(f"Error in SIP → WS stream: {str(e)}")
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info(f"SIP → WebSocket stream cancelled for call {self.call_id}")
        except Exception as e:
            logger.error(f"Fatal error in SIP → WS stream: {str(e)}")
        finally:
            logger.info(f"SIP → WebSocket audio stream ended for call {self.call_id}")

    async def _stream_websocket_to_sip(self) -> None:
        """Stream audio from WebSocket to SIP (outbound)"""
        logger.info(f"Starting WebSocket → SIP audio stream for call {self.call_id}")

        try:
            while self.is_running:
                try:
                    # Get audio from queue (with timeout)
                    platform_audio = await asyncio.wait_for(
                        self.ws_audio_queue.get(),
                        timeout=1.0
                    )

                    # Convert: PCM 16kHz → G.711 μ-law 8kHz
                    sip_audio = self.audio_converter.convert_platform_to_sip(
                        platform_audio,
                        platform_sample_rate=settings.PLATFORM_SAMPLE_RATE
                    )

                    # Send to FreeSWITCH (via ESL or other mechanism)
                    # Note: Actual implementation depends on FreeSWITCH media interface
                    # This is a placeholder for the audio output
                    # In production, you would use FreeSWITCH's media streaming API

                    # TODO: Implement actual audio output to FreeSWITCH
                    # For now, this is a stub
                    logger.debug(f"Would send {len(sip_audio)} bytes to SIP")

                except asyncio.TimeoutError:
                    # No audio available, continue
                    continue
                except Exception as e:
                    logger.error(f"Error in WS → SIP stream: {str(e)}")
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info(f"WebSocket → SIP stream cancelled for call {self.call_id}")
        except Exception as e:
            logger.error(f"Fatal error in WS → SIP stream: {str(e)}")
        finally:
            logger.info(f"WebSocket → SIP audio stream ended for call {self.call_id}")

    async def _on_voice_connector_audio(self, audio_data: bytes) -> None:
        """
        Callback for audio received from Voice Connector

        Args:
            audio_data: PCM 16-bit audio at 16kHz or 22.05kHz
        """
        try:
            # Queue audio for processing
            await self.ws_audio_queue.put(audio_data)
        except asyncio.QueueFull:
            logger.warning(f"WebSocket audio queue full for call {self.call_id}, dropping packet")

    async def _on_voice_connector_message(self, message: dict) -> None:
        """
        Callback for messages from Voice Connector

        Args:
            message: Message dictionary
        """
        msg_type = message.get("type", "")
        logger.debug(f"Received message from Voice Connector: {msg_type}")

        # Handle different message types
        if msg_type == "status":
            session_id = message.get("session_id")
            if session_id:
                self.call_info.session_id = session_id
                logger.info(f"Voice Connector session ID: {session_id}")

        elif msg_type == "error":
            error = message.get("error", "Unknown error")
            logger.error(f"Voice Connector error: {error}")
            # Consider hanging up the call
            await self.stop()

    def get_call_info(self) -> SIPCallInfo:
        """Get current call information"""
        # Update duration if still connected
        if self.call_info.connected_at and not self.call_info.disconnected_at:
            duration = (datetime.utcnow() - self.call_info.connected_at).total_seconds()
            self.call_info.duration_seconds = duration

        return self.call_info
