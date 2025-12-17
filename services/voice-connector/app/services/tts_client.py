"""
TTS Service Client
Handles communication with the Text-to-Speech service
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.schemas import SynthesisResponse

logger = get_logger(__name__)


class TTSClient:
    """Client for TTS service communication"""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize TTS client

        Args:
            base_url: TTS service base URL
        """
        self.base_url = base_url or settings.TTS_SERVICE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"TTSClient initialized with URL: {self.base_url}")

    async def start(self) -> None:
        """Start the client session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("TTS client session started")

    async def stop(self) -> None:
        """Stop the client session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("TTS client session stopped")

    async def synthesize(
        self,
        text: str,
        voice: str = "default",
        speed: float = 1.0,
        session_id: Optional[str] = None,
    ) -> Optional[SynthesisResponse]:
        """
        Synthesize speech from text

        Args:
            text: Text to synthesize
            voice: Voice ID to use
            speed: Speech speed multiplier (0.5 - 2.0)
            session_id: Session ID for logging

        Returns:
            SynthesisResponse or None if failed
        """
        if not self.session:
            await self.start()

        try:
            url = f"{self.base_url}/synthesize"

            payload = {
                "text": text,
                "voice": voice,
                "speed": speed,
            }

            logger.info(
                f"Sending synthesis request to {url} "
                f"(session: {session_id}, text_len: {len(text)})"
            )

            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(
                        f"Synthesis successful "
                        f"(session: {session_id}, "
                        f"duration: {result.get('duration_ms')}ms, "
                        f"time: {result.get('processing_time_ms')}ms)"
                    )

                    return SynthesisResponse(
                        audio_url=result.get("audio_url", ""),
                        duration_ms=result.get("duration_ms", 0),
                        processing_time_ms=result.get("processing_time_ms", 0),
                        text=result.get("text", text),
                        format=result.get("format", "wav"),
                    )
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Synthesis failed with status {response.status}: "
                        f"{error_text} (session: {session_id})"
                    )
                    return None

        except asyncio.TimeoutError:
            logger.error(f"Synthesis timeout (session: {session_id})")
            return None
        except Exception as e:
            logger.error(f"Synthesis error: {e} (session: {session_id})")
            return None

    async def download_audio(self, audio_url: str) -> Optional[bytes]:
        """
        Download audio from URL

        Args:
            audio_url: URL to download audio from

        Returns:
            Audio bytes or None if failed
        """
        if not self.session:
            await self.start()

        try:
            logger.debug(f"Downloading audio from {audio_url}")

            async with self.session.get(audio_url) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    logger.info(f"Downloaded {len(audio_data)} bytes of audio")
                    return audio_data
                else:
                    logger.error(
                        f"Audio download failed with status {response.status}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Audio download error: {e}")
            return None

    async def health_check(self) -> bool:
        """
        Check if TTS service is healthy

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
                    logger.debug(f"TTS health check: {result.get('status')}")
                    return result.get("status") == "healthy"
                return False
        except Exception as e:
            logger.error(f"TTS health check error: {e}")
            return False

    def __del__(self):
        """Cleanup on deletion"""
        if self.session:
            logger.warning("TTSClient deleted with active session")
