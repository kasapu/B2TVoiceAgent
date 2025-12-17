"""
Call Router
Routes incoming SIP calls and manages active call bridges
"""
import asyncio
from typing import Dict, Optional, List
from datetime import datetime
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.schemas import SIPCallInfo, ESLEvent, CallMetrics
from app.services.esl_handler import ESLHandler
from app.services.sip_call_bridge import SIPCallBridge

logger = get_logger(__name__)


class CallRouter:
    """
    Manages SIP call routing and active call bridges

    This router:
    - Listens for FreeSWITCH call events
    - Creates SIPCallBridge for each incoming call
    - Manages active bridges
    - Provides call metrics and status
    """

    def __init__(self):
        """Initialize call router"""
        self.esl_handler = ESLHandler()
        self.active_bridges: Dict[str, SIPCallBridge] = {}
        self.call_metrics = CallMetrics()
        self.is_running = False

        logger.info("CallRouter initialized")

    async def start(self) -> bool:
        """
        Start the call router

        Returns:
            True if started successfully
        """
        try:
            logger.info("Starting CallRouter")

            # Connect to FreeSWITCH ESL
            connected = await self.esl_handler.connect()
            if not connected:
                logger.error("Failed to connect to FreeSWITCH ESL")
                return False

            # Register event callbacks
            self.esl_handler.register_event_callback(
                "CHANNEL_CREATE",
                self._on_channel_create
            )
            self.esl_handler.register_event_callback(
                "CHANNEL_ANSWER",
                self._on_channel_answer
            )
            self.esl_handler.register_event_callback(
                "CHANNEL_HANGUP",
                self._on_channel_hangup
            )

            self.is_running = True
            logger.info("CallRouter started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start CallRouter: {str(e)}")
            return False

    async def stop(self) -> None:
        """Stop the call router"""
        logger.info("Stopping CallRouter")

        self.is_running = False

        # Stop all active bridges
        bridge_ids = list(self.active_bridges.keys())
        for unique_id in bridge_ids:
            await self._stop_bridge(unique_id)

        # Disconnect from FreeSWITCH
        await self.esl_handler.disconnect()

        logger.info("CallRouter stopped")

    async def _on_channel_create(self, event: ESLEvent) -> None:
        """
        Handle CHANNEL_CREATE event

        Args:
            event: ESL event
        """
        logger.info(f"Channel created: {event.unique_id} from {event.caller_number}")

        # Check if we've reached max concurrent calls
        if len(self.active_bridges) >= settings.MAX_CONCURRENT_CALLS:
            logger.warning(f"Max concurrent calls reached ({settings.MAX_CONCURRENT_CALLS}), rejecting call")
            await self.esl_handler.hangup_call(event.unique_id)
            return

        # Create call bridge
        try:
            bridge = SIPCallBridge(
                sip_call_id=event.headers.get("variable_sip_call_id", event.unique_id),
                unique_id=event.unique_id,
                caller_number=event.caller_number or "Unknown",
                callee_number=event.callee_number or "Unknown",
                esl_handler=self.esl_handler
            )

            self.active_bridges[event.unique_id] = bridge
            self.call_metrics.total_calls += 1
            self.call_metrics.active_calls = len(self.active_bridges)

            logger.info(f"Created bridge for call {event.unique_id} (total: {self.call_metrics.total_calls})")

        except Exception as e:
            logger.error(f"Failed to create bridge for call {event.unique_id}: {str(e)}")
            await self.esl_handler.hangup_call(event.unique_id)

    async def _on_channel_answer(self, event: ESLEvent) -> None:
        """
        Handle CHANNEL_ANSWER event

        Args:
            event: ESL event
        """
        logger.info(f"Channel answered: {event.unique_id}")

        # Get bridge for this call
        bridge = self.active_bridges.get(event.unique_id)
        if not bridge:
            logger.warning(f"No bridge found for answered call {event.unique_id}")
            return

        # Start bridging
        try:
            success = await bridge.start()
            if not success:
                logger.error(f"Failed to start bridge for call {event.unique_id}")
                await self._stop_bridge(event.unique_id)
                await self.esl_handler.hangup_call(event.unique_id)
        except Exception as e:
            logger.error(f"Error starting bridge for call {event.unique_id}: {str(e)}")
            await self._stop_bridge(event.unique_id)

    async def _on_channel_hangup(self, event: ESLEvent) -> None:
        """
        Handle CHANNEL_HANGUP event

        Args:
            event: ESL event
        """
        logger.info(f"Channel hangup: {event.unique_id}")

        # Stop bridge for this call
        await self._stop_bridge(event.unique_id)

    async def _stop_bridge(self, unique_id: str) -> None:
        """
        Stop bridge for a call

        Args:
            unique_id: Call unique ID
        """
        bridge = self.active_bridges.get(unique_id)
        if not bridge:
            return

        try:
            # Stop the bridge
            await bridge.stop()

            # Update metrics
            call_info = bridge.get_call_info()
            self.call_metrics.completed_calls += 1
            self.call_metrics.total_duration_seconds += call_info.duration_seconds

            if self.call_metrics.completed_calls > 0:
                self.call_metrics.average_duration_seconds = (
                    self.call_metrics.total_duration_seconds / self.call_metrics.completed_calls
                )

            logger.info(
                f"Bridge stopped for call {unique_id} "
                f"(duration: {call_info.duration_seconds:.1f}s)"
            )

        except Exception as e:
            logger.error(f"Error stopping bridge for call {unique_id}: {str(e)}")
        finally:
            # Remove from active bridges
            if unique_id in self.active_bridges:
                del self.active_bridges[unique_id]
                self.call_metrics.active_calls = len(self.active_bridges)

    def get_active_calls(self) -> List[SIPCallInfo]:
        """
        Get list of active calls

        Returns:
            List of SIPCallInfo
        """
        calls = []
        for bridge in self.active_bridges.values():
            calls.append(bridge.get_call_info())
        return calls

    def get_metrics(self) -> CallMetrics:
        """
        Get call metrics

        Returns:
            CallMetrics
        """
        self.call_metrics.active_calls = len(self.active_bridges)
        return self.call_metrics

    def get_bridge(self, unique_id: str) -> Optional[SIPCallBridge]:
        """
        Get bridge for specific call

        Args:
            unique_id: Call unique ID

        Returns:
            SIPCallBridge or None
        """
        return self.active_bridges.get(unique_id)
