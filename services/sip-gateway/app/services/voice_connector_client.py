"""
Voice Connector WebSocket Client
Connects to the existing Voice Connector service via WebSocket
"""
import asyncio
import json
from typing import Optional, Callable
import websockets
from websockets.client import WebSocketClientProtocol
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class VoiceConnectorClient:
    """
    WebSocket client for connecting to Voice Connector service

    This client:
    - Connects to the Voice Connector WebSocket endpoint
    - Sends/receives binary audio frames
    - Handles JSON control messages
    - Manages connection lifecycle and reconnection
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize Voice Connector client

        Args:
            base_url: WebSocket URL (e.g., ws://voice-connector:8005)
        """
        self.base_url = base_url or settings.VOICE_CONNECTOR_URL
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.is_connected = False
        self.reconnect_delay = settings.WS_RECONNECT_DELAY

        # Callbacks
        self.on_audio_callback: Optional[Callable] = None
        self.on_message_callback: Optional[Callable] = None
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None

        # Tasks
        self.receive_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

        logger.info(f"VoiceConnectorClient initialized for {self.base_url}")

    async def connect(self) -> bool:
        """
        Connect to Voice Connector WebSocket

        Returns:
            True if connection successful, False otherwise
        """
        try:
            ws_url = f"{self.base_url}/ws/voice"
            logger.info(f"Connecting to Voice Connector: {ws_url}")

            self.websocket = await websockets.connect(
                ws_url,
                ping_interval=settings.WS_HEARTBEAT_INTERVAL,
                ping_timeout=settings.WS_TIMEOUT,
                close_timeout=10
            )

            self.is_connected = True
            logger.info("Connected to Voice Connector successfully")

            # Wait for initial status message
            try:
                initial_message = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=5.0
                )
                if isinstance(initial_message, str):
                    status = json.loads(initial_message)
                    logger.info(f"Received initial status: {status}")
            except asyncio.TimeoutError:
                logger.warning("No initial status message received")

            # Start receiving messages
            self.receive_task = asyncio.create_task(self._receive_loop())

            # Start heartbeat
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # Call connection callback
            if self.on_connect_callback:
                await self.on_connect_callback()

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Voice Connector: {str(e)}")
            self.is_connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Voice Connector"""
        logger.info("Disconnecting from Voice Connector")

        self.is_connected = False

        # Cancel tasks
        if self.receive_task and not self.receive_task.done():
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass

        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {str(e)}")
            self.websocket = None

        # Call disconnect callback
        if self.on_disconnect_callback:
            await self.on_disconnect_callback()

        logger.info("Disconnected from Voice Connector")

    async def send_audio(self, audio_data: bytes) -> bool:
        """
        Send audio data to Voice Connector

        Args:
            audio_data: Binary audio data (PCM 16-bit 16kHz)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_connected or not self.websocket:
            logger.warning("Cannot send audio: not connected")
            return False

        try:
            await self.websocket.send(audio_data)
            return True
        except Exception as e:
            logger.error(f"Failed to send audio: {str(e)}")
            return False

    async def send_message(self, message: dict) -> bool:
        """
        Send JSON control message to Voice Connector

        Args:
            message: Message dictionary

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_connected or not self.websocket:
            logger.warning("Cannot send message: not connected")
            return False

        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False

    async def _receive_loop(self) -> None:
        """Receive messages from Voice Connector"""
        logger.info("Starting receive loop")

        try:
            while self.is_connected and self.websocket:
                try:
                    message = await self.websocket.recv()

                    # Handle binary audio
                    if isinstance(message, bytes):
                        if self.on_audio_callback:
                            await self.on_audio_callback(message)

                    # Handle JSON messages
                    elif isinstance(message, str):
                        try:
                            msg_data = json.loads(message)
                            if self.on_message_callback:
                                await self.on_message_callback(msg_data)
                        except json.JSONDecodeError:
                            logger.warning(f"Received invalid JSON: {message}")

                except websockets.exceptions.ConnectionClosed:
                    logger.warning("Voice Connector connection closed")
                    break
                except Exception as e:
                    logger.error(f"Error in receive loop: {str(e)}")
                    break

        except asyncio.CancelledError:
            logger.info("Receive loop cancelled")
        except Exception as e:
            logger.error(f"Receive loop error: {str(e)}")
        finally:
            self.is_connected = False
            logger.info("Receive loop ended")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to keep connection alive"""
        logger.info("Starting heartbeat loop")

        try:
            while self.is_connected and self.websocket:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)

                try:
                    # Send ping message
                    await self.send_message({"type": "ping"})
                except Exception as e:
                    logger.error(f"Failed to send heartbeat: {str(e)}")
                    break

        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")
        except Exception as e:
            logger.error(f"Heartbeat loop error: {str(e)}")

    def set_on_audio_callback(self, callback: Callable) -> None:
        """Set callback for received audio"""
        self.on_audio_callback = callback

    def set_on_message_callback(self, callback: Callable) -> None:
        """Set callback for received messages"""
        self.on_message_callback = callback

    def set_on_connect_callback(self, callback: Callable) -> None:
        """Set callback for connection established"""
        self.on_connect_callback = callback

    def set_on_disconnect_callback(self, callback: Callable) -> None:
        """Set callback for disconnection"""
        self.on_disconnect_callback = callback
