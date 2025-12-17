"""
FreeSWITCH Event Socket Layer (ESL) Handler
Manages connection to FreeSWITCH and handles events
"""
import asyncio
from typing import Optional, Callable, Dict
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.schemas import ESLEvent, ESLEventType

logger = get_logger(__name__)


class ESLHandler:
    """
    FreeSWITCH Event Socket Layer client

    This handler:
    - Connects to FreeSWITCH via Event Socket (port 8021)
    - Subscribes to call events
    - Provides audio streaming interface
    - Manages call control commands
    """

    def __init__(self):
        """Initialize ESL handler"""
        self.host = settings.FREESWITCH_HOST
        self.port = settings.FREESWITCH_ESL_PORT
        self.password = settings.FREESWITCH_ESL_PASSWORD

        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.is_connected = False

        # Event callbacks
        self.event_callbacks: Dict[str, Callable] = {}

        # Tasks
        self.event_loop_task: Optional[asyncio.Task] = None

        logger.info(f"ESLHandler initialized for {self.host}:{self.port}")

    async def connect(self) -> bool:
        """
        Connect to FreeSWITCH Event Socket

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to FreeSWITCH ESL at {self.host}:{self.port}")

            # Open TCP connection
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )

            # Read initial greeting
            greeting = await self._read_response()
            if not greeting.startswith("Content-Type: auth/request"):
                logger.error(f"Unexpected greeting: {greeting}")
                return False

            # Authenticate
            auth_command = f"auth {self.password}\n\n"
            self.writer.write(auth_command.encode())
            await self.writer.drain()

            # Read auth response
            auth_response = await self._read_response()
            if "Reply-Text: +OK accepted" not in auth_response:
                logger.error(f"Authentication failed: {auth_response}")
                return False

            logger.info("Authenticated with FreeSWITCH ESL")

            # Subscribe to events
            await self._subscribe_events()

            self.is_connected = True

            # Start event loop
            self.event_loop_task = asyncio.create_task(self._event_loop())

            logger.info("Connected to FreeSWITCH ESL successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to FreeSWITCH ESL: {str(e)}")
            self.is_connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from FreeSWITCH ESL"""
        logger.info("Disconnecting from FreeSWITCH ESL")

        self.is_connected = False

        # Cancel event loop
        if self.event_loop_task and not self.event_loop_task.done():
            self.event_loop_task.cancel()
            try:
                await self.event_loop_task
            except asyncio.CancelledError:
                pass

        # Close connection
        if self.writer:
            try:
                self.writer.write(b"exit\n\n")
                await self.writer.drain()
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f"Error closing ESL connection: {str(e)}")

        self.reader = None
        self.writer = None

        logger.info("Disconnected from FreeSWITCH ESL")

    async def _subscribe_events(self) -> None:
        """Subscribe to FreeSWITCH events"""
        events = [
            "CHANNEL_CREATE",
            "CHANNEL_ANSWER",
            "CHANNEL_BRIDGE",
            "CHANNEL_HANGUP",
            "CHANNEL_DESTROY"
        ]

        for event in events:
            command = f"event plain {event}\n\n"
            self.writer.write(command.encode())
            await self.writer.drain()

            response = await self._read_response()
            logger.debug(f"Subscribe {event}: {response}")

    async def _event_loop(self) -> None:
        """Main event processing loop"""
        logger.info("Starting ESL event loop")

        try:
            while self.is_connected and self.reader:
                try:
                    # Read event
                    event_data = await self._read_response()

                    if event_data:
                        # Parse event
                        event = self._parse_event(event_data)
                        if event:
                            await self._handle_event(event)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in event loop: {str(e)}")
                    await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Event loop error: {str(e)}")
        finally:
            self.is_connected = False
            logger.info("ESL event loop ended")

    async def _read_response(self) -> str:
        """
        Read response from ESL

        Returns:
            Response string
        """
        if not self.reader:
            return ""

        try:
            # Read until we get a blank line
            lines = []
            content_length = 0

            while True:
                line = await self.reader.readline()
                if not line:
                    break

                line_str = line.decode('utf-8').strip()
                lines.append(line_str)

                # Check for Content-Length header
                if line_str.startswith("Content-Length:"):
                    content_length = int(line_str.split(":")[1].strip())

                # Empty line indicates end of headers
                if line_str == "":
                    break

            # Read body if Content-Length specified
            if content_length > 0:
                body = await self.reader.readexactly(content_length)
                lines.append(body.decode('utf-8'))

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error reading ESL response: {str(e)}")
            return ""

    def _parse_event(self, event_data: str) -> Optional[ESLEvent]:
        """
        Parse ESL event data

        Args:
            event_data: Raw event data

        Returns:
            ESLEvent or None
        """
        try:
            lines = event_data.split("\n")
            headers = {}
            body = ""

            in_body = False
            for line in lines:
                if in_body:
                    body += line + "\n"
                elif ": " in line:
                    key, value = line.split(": ", 1)
                    headers[key] = value
                elif line == "":
                    in_body = True

            event_name = headers.get("Event-Name", "")
            if not event_name:
                return None

            # Create ESLEvent
            event = ESLEvent(
                event_type=event_name,
                unique_id=headers.get("Unique-ID", ""),
                caller_number=headers.get("Caller-Caller-ID-Number"),
                callee_number=headers.get("Caller-Destination-Number"),
                call_state=headers.get("Channel-Call-State"),
                headers=headers,
                body=body.strip() if body else None
            )

            return event

        except Exception as e:
            logger.error(f"Error parsing ESL event: {str(e)}")
            return None

    async def _handle_event(self, event: ESLEvent) -> None:
        """
        Handle ESL event

        Args:
            event: ESL event
        """
        logger.debug(f"Received event: {event.event_type} (call: {event.unique_id})")

        # Call registered callback for this event type
        if event.event_type in self.event_callbacks:
            callback = self.event_callbacks[event.event_type]
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {str(e)}")

    def register_event_callback(self, event_type: str, callback: Callable) -> None:
        """
        Register callback for specific event type

        Args:
            event_type: Event type (e.g., "CHANNEL_ANSWER")
            callback: Async callback function
        """
        self.event_callbacks[event_type] = callback
        logger.info(f"Registered callback for {event_type}")

    async def send_command(self, command: str) -> str:
        """
        Send command to FreeSWITCH

        Args:
            command: Command string

        Returns:
            Response string
        """
        if not self.is_connected or not self.writer:
            logger.warning("Cannot send command: not connected")
            return ""

        try:
            # Send command
            command_str = f"{command}\n\n"
            self.writer.write(command_str.encode())
            await self.writer.drain()

            # Read response
            response = await self._read_response()
            return response

        except Exception as e:
            logger.error(f"Error sending command: {str(e)}")
            return ""

    async def answer_call(self, unique_id: str) -> bool:
        """
        Answer incoming call

        Args:
            unique_id: Call unique ID

        Returns:
            True if successful
        """
        response = await self.send_command(f"api uuid_answer {unique_id}")
        return "+OK" in response

    async def hangup_call(self, unique_id: str) -> bool:
        """
        Hangup call

        Args:
            unique_id: Call unique ID

        Returns:
            True if successful
        """
        response = await self.send_command(f"api uuid_kill {unique_id}")
        return "+OK" in response
