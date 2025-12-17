"""gTTS (Google Text-to-Speech) model manager - Lightweight TTS solution."""

import logging
from typing import Optional
from gtts import gTTS
from app.core.config import settings

logger = logging.getLogger(__name__)


class TTSModelManager:
    """
    Singleton class to manage gTTS (Google Text-to-Speech).
    Lightweight alternative to Coqui TTS for easier deployment.
    """

    _instance: Optional["TTSModelManager"] = None
    _available_voices: list = ["default", "en-US", "en-GB", "en-AU", "en-IN"]
    _available_languages: list = ["en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko"]

    def __new__(cls):
        """Singleton pattern - only one instance allowed."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the model manager."""
        logger.info("gTTS model manager initialized")
        logger.info(f"Available languages: {', '.join(self._available_languages)}")

    def load_model(self) -> None:
        """Load model (no-op for gTTS, but kept for compatibility)."""
        logger.info("Using gTTS (Google Text-to-Speech) - no model loading needed")
        logger.info("gTTS is ready for synthesis")

    def get_device(self) -> str:
        """Get device (always CPU for gTTS)."""
        return "cpu"

    def get_available_voices(self) -> list:
        """Get list of available voice IDs."""
        return self._available_voices

    def synthesize(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> None:
        """
        Synthesize speech from text using gTTS.

        Args:
            text: Text to synthesize
            output_path: Path to save output audio file
            voice: Voice/accent (e.g., en-US, en-GB, default)
            speed: Speech speed (gTTS has limited speed support)

        Raises:
            RuntimeError: If synthesis fails
        """
        logger.info(f"Synthesizing text: {text[:50]}...")
        logger.info(f"Output path: {output_path}")
        logger.info(f"Voice: {voice or 'default'}, Speed: {speed}")

        try:
            # Parse voice/language from voice parameter
            lang = "en"
            tld = "com"  # Top-level domain for accent

            if voice and voice != "default":
                if voice == "en-US":
                    lang, tld = "en", "com"
                elif voice == "en-GB":
                    lang, tld = "en", "co.uk"
                elif voice == "en-AU":
                    lang, tld = "en", "com.au"
                elif voice == "en-IN":
                    lang, tld = "en", "co.in"
                elif len(voice) == 2:  # Language code like "es", "fr"
                    lang = voice

            # Create gTTS instance
            # Note: gTTS doesn't support speed adjustment directly
            # We use 'slow' parameter for slower speech
            slow = (speed < 0.9)

            tts = gTTS(
                text=text,
                lang=lang,
                tld=tld,
                slow=slow
            )

            # Save to file
            tts.save(output_path)

            logger.info(f"Synthesis completed successfully")

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            raise RuntimeError(f"Synthesis failed: {e}")

    def is_multi_speaker(self) -> bool:
        """Check if model supports multiple speakers."""
        return True  # gTTS supports multiple accents


# Global model manager instance
model_manager = TTSModelManager()
