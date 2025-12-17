"""Core transcription service logic."""

import time
import logging
from typing import Optional, List
from fastapi import UploadFile
from app.models.whisper_model import model_manager
from app.services.audio_processor import AudioProcessor
from app.models.schemas import TranscribeResponse, Segment
from app.core.config import settings

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service for transcribing audio files."""

    @staticmethod
    async def transcribe_audio(
        file: UploadFile,
        language: Optional[str] = None,
        task: str = "transcribe",
        beam_size: int = 5,
        temperature: float = 0.0
    ) -> TranscribeResponse:
        """
        Transcribe an uploaded audio file.

        Args:
            file: Uploaded audio file
            language: Language code (auto-detect if None)
            task: "transcribe" or "translate"
            beam_size: Beam size for decoding
            temperature: Temperature for sampling

        Returns:
            TranscribeResponse: Transcription result with metadata

        Raises:
            Exception: If transcription fails
        """
        audio_path = None
        converted_path = None

        try:
            start_time = time.time()

            # Validate file format
            if not AudioProcessor.validate_audio_format(file.filename):
                raise ValueError(
                    f"Unsupported audio format. Supported formats: {', '.join(settings.SUPPORTED_FORMATS)}"
                )

            # Step 1: Save uploaded file
            logger.info(f"Processing file: {file.filename}")
            audio_path = await AudioProcessor.save_upload(file)

            # Step 2: Convert to WAV if needed
            if not audio_path.lower().endswith(".wav"):
                logger.info("Converting audio to WAV format")
                converted_path = AudioProcessor.convert_to_wav(audio_path)
                transcribe_path = converted_path
            else:
                transcribe_path = audio_path

            # Step 3: Get audio duration
            duration = AudioProcessor.get_audio_duration(transcribe_path)

            # Step 4: Transcribe using Whisper
            logger.info("Starting transcription...")
            segments, info = model_manager.transcribe(
                transcribe_path,
                language=language,
                task=task,
                beam_size=beam_size,
                temperature=temperature
            )

            # Step 5: Process segments
            full_text = ""
            segment_list: List[Segment] = []

            for i, segment in enumerate(segments):
                full_text += segment.text
                segment_list.append(
                    Segment(
                        id=i,
                        start=segment.start,
                        end=segment.end,
                        text=segment.text.strip()
                    )
                )

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(f"Transcription completed in {processing_time_ms}ms")
            logger.info(f"Detected language: {info.language}")
            logger.info(f"Text: {full_text.strip()[:100]}...")

            # Step 6: Cleanup temporary files
            if settings.CLEANUP_AFTER_TRANSCRIBE:
                AudioProcessor.cleanup_files(audio_path, converted_path)

            return TranscribeResponse(
                text=full_text.strip(),
                language=info.language,
                duration=duration,
                segments=segment_list if segment_list else None,
                processing_time_ms=processing_time_ms
            )

        except Exception as e:
            # Cleanup on error
            if audio_path:
                AudioProcessor.cleanup_files(audio_path, converted_path)

            logger.error(f"Transcription failed: {e}")
            raise

    @staticmethod
    def get_service_health() -> dict:
        """
        Get service health status including model and device info.

        Returns:
            dict: Health status information
        """
        try:
            from app.core.gpu_detector import get_device_info

            return {
                "status": "healthy",
                "model": settings.WHISPER_MODEL,
                "device": model_manager.get_device(),
                "compute_type": model_manager.get_compute_type(),
                "device_info": get_device_info()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
