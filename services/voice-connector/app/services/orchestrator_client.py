"""
Orchestrator Service Client
Handles communication with the Orchestrator service
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.schemas import ConversationResponse

logger = get_logger(__name__)


class OrchestratorClient:
    """Client for Orchestrator service communication"""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize Orchestrator client

        Args:
            base_url: Orchestrator service base URL
        """
        self.base_url = base_url or settings.ORCHESTRATOR_URL
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"OrchestratorClient initialized with URL: {self.base_url}")

    async def start(self) -> None:
        """Start the client session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Orchestrator client session started")

    async def stop(self) -> None:
        """Stop the client session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Orchestrator client session stopped")

    async def send_message(
        self,
        session_id: str,
        user_message: str,
        channel: str = "voice",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ConversationResponse]:
        """
        Send a message to the orchestrator

        Args:
            session_id: Conversation session ID
            user_message: User's message text
            channel: Communication channel (default: "voice")
            metadata: Additional metadata

        Returns:
            ConversationResponse or None if failed
        """
        if not self.session:
            await self.start()

        try:
            url = f"{self.base_url}/api/v1/conversation"

            payload = {
                "session_id": session_id,
                "user_message": user_message,
                "channel": channel,
                "metadata": metadata or {},
            }

            logger.info(
                f"Sending message to orchestrator "
                f"(session: {session_id}, message_len: {len(user_message)})"
            )

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(
                        f"Got orchestrator response "
                        f"(session: {session_id}, "
                        f"intent: {result.get('intent')}, "
                        f"response_len: {len(result.get('response', ''))})"
                    )

                    return ConversationResponse(
                        response=result.get("response", ""),
                        intent=result.get("intent"),
                        entities=result.get("entities", {}),
                        session_id=result.get("session_id", session_id),
                        metadata=result.get("metadata", {}),
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Orchestrator request failed with status {response.status}: "
                        f"{error_text} (session: {session_id})"
                    )
                    return None

        except asyncio.TimeoutError:
            logger.error(f"Orchestrator timeout (session: {session_id})")
            return None
        except Exception as e:
            logger.error(f"Orchestrator error: {e} (session: {session_id})")
            return None

    async def create_session(self, channel: str = "voice") -> Optional[str]:
        """
        Create a new conversation session

        Args:
            channel: Communication channel

        Returns:
            Session ID or None if failed
        """
        if not self.session:
            await self.start()

        try:
            url = f"{self.base_url}/api/v1/session"

            payload = {"channel": channel}

            logger.info("Creating new session")

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    session_id = result.get("session_id")
                    logger.info(f"Created session: {session_id}")
                    return session_id
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Session creation failed with status {response.status}: "
                        f"{error_text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Session creation error: {e}")
            return None

    async def health_check(self) -> bool:
        """
        Check if Orchestrator service is healthy

        Returns:
            True if healthy, False otherwise
        """
        if not self.session:
            await self.start()

        try:
            url = f"{self.base_url}/health"
            async with self.session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.debug(f"Orchestrator health check: {result.get('status')}")
                    return result.get("status") == "healthy"
                return False
        except Exception as e:
            logger.error(f"Orchestrator health check error: {e}")
            return False

    def __del__(self):
        """Cleanup on deletion"""
        if self.session:
            logger.warning("OrchestratorClient deleted with active session")
