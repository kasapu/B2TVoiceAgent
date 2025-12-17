"""Whisper model loader and manager (Singleton)."""

import logging
from typing import Optional
from faster_whisper import WhisperModel
from app.core.config import settings
from app.core.gpu_detector import detect_device

logger = logging.getLogger(__name__)


class WhisperModelManager:
    """
    Singleton class to manage Whisper model loading and inference.
    Ensures only one model instance is loaded in memory.
    """

    _instance: Optional["WhisperModelManager"] = None
    _model: Optional[WhisperModel] = None
    _device: Optional[str] = None
    _compute_type: Optional[str] = None

    def __new__(cls):
        """Singleton pattern - only one instance allowed."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the model manager (only once)."""
        if self._model is None:
            self.load_model()

    def load_model(self) -> None:
        """Load the Whisper model with auto-detected device settings."""
        try:
            # Determine device and compute type
            if settings.DEVICE == "auto":
                self._device, self._compute_type = detect_device()
            else:
                self._device = settings.DEVICE
                self._compute_type = (
                    settings.COMPUTE_TYPE if settings.COMPUTE_TYPE != "auto"
                    else ("float16" if settings.DEVICE == "cuda" else "int8")
                )

            logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
            logger.info(f"Device: {self._device}, Compute type: {self._compute_type}")

            # Load the model
            self._model = WhisperModel(
                settings.WHISPER_MODEL,
                device=self._device,
                compute_type=self._compute_type,
                download_root=settings.DOWNLOAD_ROOT,
                cpu_threads=settings.CPU_THREADS if self._device == "cpu" else 0,
                num_workers=settings.NUM_WORKERS
            )

            logger.info(f"Whisper model '{settings.WHISPER_MODEL}' loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise RuntimeError(f"Failed to load Whisper model: {e}")

    def get_model(self) -> WhisperModel:
        """
        Get the loaded Whisper model instance.

        Returns:
            WhisperModel: The loaded Whisper model

        Raises:
            RuntimeError: If model is not loaded
        """
        if self._model is None:
            raise RuntimeError("Whisper model not loaded")
        return self._model

    def get_device(self) -> str:
        """Get the device being used (cpu/cuda)."""
        return self._device or "unknown"

    def get_compute_type(self) -> str:
        """Get the compute type being used."""
        return self._compute_type or "unknown"

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        beam_size: int = 5,
        temperature: float = 0.0
    ) -> tuple:
        """
        Transcribe audio file using the loaded Whisper model.

        Args:
            audio_path: Path to audio file
            language: Language code (auto-detect if None)
            task: "transcribe" or "translate"
            beam_size: Beam size for decoding
            temperature: Temperature for sampling

        Returns:
            tuple: (segments, info) from faster-whisper
        """
        if self._model is None:
            raise RuntimeError("Whisper model not loaded")

        logger.info(f"Transcribing audio: {audio_path}")
        logger.info(f"Parameters: language={language}, task={task}, beam_size={beam_size}")

        try:
            segments, info = self._model.transcribe(
                audio_path,
                language=language,
                task=task,
                beam_size=beam_size,
                temperature=temperature,
                vad_filter=settings.VAD_FILTER,
                vad_parameters={
                    "threshold": settings.VAD_THRESHOLD
                } if settings.VAD_FILTER else None
            )

            return segments, info

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {e}")


# Global model manager instance
model_manager = WhisperModelManager()
