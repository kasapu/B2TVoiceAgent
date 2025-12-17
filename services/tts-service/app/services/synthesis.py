"""Core text-to-speech synthesis service logic."""

import time
import logging
from app.models.tts_model import model_manager
from app.services.audio_storage import AudioStorageService
from app.models.schemas import SynthesizeRequest, SynthesizeResponse
from app.core.config import settings

logger = logging.getLogger(__name__)


class SynthesisService:
    """Service for synthesizing speech from text."""

    @staticmethod
    async def synthesize_speech(request: SynthesizeRequest) -> SynthesizeResponse:
        """
        Synthesize speech from text and upload to MinIO.

        Args:
            request: Synthesis request with text, voice, and parameters

        Returns:
            SynthesizeResponse: Response with audio URL and metadata

        Raises:
            Exception: If synthesis or upload fails
        """
        temp_path = None
        adjusted_path = None

        try:
            start_time = time.time()

            logger.info(f"Synthesizing text: '{request.text[:50]}...'")
            logger.info(f"Voice: {request.voice}, Speed: {request.speed}")

            # Step 1: Generate unique filename and paths
            local_filename, minio_object_name = AudioStorageService.generate_unique_filename("wav")
            temp_path = AudioStorageService.get_local_path(local_filename)

            # Step 2: Synthesize speech using TTS model
            logger.info("Running TTS synthesis...")
            model_manager.synthesize(
                text=request.text,
                output_path=temp_path,
                voice=request.voice if request.voice != "default" else None,
                speed=1.0  # Apply speed adjustment separately
            )

            # Step 3: Apply speed adjustment if needed
            if request.speed != 1.0:
                adjusted_filename = f"adjusted_{local_filename}"
                adjusted_path = AudioStorageService.get_local_path(adjusted_filename)

                AudioStorageService.apply_speed_adjustment(
                    input_path=temp_path,
                    output_path=adjusted_path,
                    speed=request.speed
                )

                # Use adjusted file for upload
                final_path = adjusted_path
            else:
                final_path = temp_path

            # Step 4: Get audio duration
            duration_ms = AudioStorageService.get_audio_duration(final_path)

            # Step 5: Upload to MinIO and get presigned URL
            logger.info("Uploading to MinIO...")
            audio_url = await AudioStorageService.store_audio(final_path, minio_object_name)

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(f"Synthesis completed in {processing_time_ms}ms")
            logger.info(f"Audio URL: {audio_url[:80]}...")

            # Step 6: Cleanup temporary files
            if settings.CLEANUP_AFTER_UPLOAD:
                AudioStorageService.cleanup_local_files(temp_path, adjusted_path)

            return SynthesizeResponse(
                audio_url=audio_url,
                duration_ms=duration_ms,
                processing_time_ms=processing_time_ms,
                text=request.text,
                voice=request.voice,
                format=settings.OUTPUT_FORMAT,
                sample_rate=settings.SAMPLE_RATE
            )

        except Exception as e:
            # Cleanup on error
            if temp_path:
                AudioStorageService.cleanup_local_files(temp_path, adjusted_path)

            logger.error(f"Synthesis failed: {e}")
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
            from app.core.minio_client import minio_client

            # Check MinIO connection
            minio_connected = False
            try:
                minio_client._client.bucket_exists(settings.MINIO_BUCKET)
                minio_connected = True
            except Exception as e:
                logger.warning(f"MinIO connection check failed: {e}")

            return {
                "status": "healthy",
                "model": settings.TTS_MODEL,
                "device": model_manager.get_device(),
                "device_info": get_device_info(),
                "minio_connected": minio_connected,
                "available_voices": model_manager.get_available_voices()
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
