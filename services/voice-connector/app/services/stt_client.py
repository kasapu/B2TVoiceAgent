"""
STT Service Client
Handles communication with the Speech-to-Text service
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from io import BytesIO
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.schemas import TranscriptionResponse

logger = get_logger(__name__)


class STTClient:
    """Client for STT service communication"""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize STT client

        Args:
            base_url: STT service base URL
        """
        self.base_url = base_url or settings.STT_SERVICE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"STTClient initialized with URL: {self.base_url}")

    async def start(self) -> None:
        """Start the client session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("STT client session started")

    async def stop(self) -> None:
        """Stop the client session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("STT client session stopped")

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "en",
        session_id: Optional[str] = None,
    ) -> Optional[TranscriptionResponse]:
        """
        Transcribe audio to text

        Args:
            audio_data: Audio data in WAV format
            language: Language code (default: "en")
            session_id: Session ID for logging

        Returns:
            TranscriptionResponse or None if failed
        """
        if not self.session:
            await self.start()

        try:
            # Prepare multipart form data
            data = aiohttp.FormData()
            data.add_field(
                "file",
                BytesIO(audio_data),
                filename="audio.wav",
                content_type="audio/wav",
            )
            data.add_field("language", language)
            data.add_field("task", "transcribe")

            url = f"{self.base_url}/transcribe"

            logger.info(
                f"Sending transcription request to {url} "
                f"(session: {session_id}, size: {len(audio_data)} bytes)"
            )

            async with self.session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(
                        f"Transcription successful: '{result.get('text')}' "
                        f"(session: {session_id}, "
                        f"time: {result.get('processing_time_ms')}ms)"
                    )

                    return TranscriptionResponse(
                        text=result.get("text", ""),
                        language=result.get("language", language),
                        duration=result.get("duration", 0.0),
                        confidence=result.get("confidence"),
                        processing_time_ms=result.get("processing_time_ms", 0),
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Transcription failed with status {response.status}: "
                        f"{error_text} (session: {session_id})"
                    )
                    return None

        except asyncio.TimeoutError:
            logger.error(f"Transcription timeout (session: {session_id})")
            return None
        except Exception as e:
            logger.error(f"Transcription error: {e} (session: {session_id})")
            return None

    async def health_check(self) -> bool:
        """
        Check if STT service is healthy

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
                    logger.debug(f"STT health check: {result.get('status')}")
                    return result.get("status") == "healthy"
                return False
        except Exception as e:
            logger.error(f"STT health check error: {e}")
            return False

    def __del__(self):
        """Cleanup on deletion"""
        if self.session:
            logger.warning("STTClient deleted with active session")
