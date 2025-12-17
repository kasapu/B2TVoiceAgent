"""Audio storage service for MinIO integration."""

import os
import uuid
import logging
from pydub import AudioSegment
from app.core.config import settings
from app.core.minio_client import minio_client

logger = logging.getLogger(__name__)


class AudioStorageService:
    """Service for handling audio file storage and retrieval."""

    @staticmethod
    def generate_unique_filename(extension: str = "wav") -> tuple[str, str]:
        """
        Generate unique filename and object path for MinIO.

        Args:
            extension: File extension without dot

        Returns:
            tuple: (local_filename, minio_object_name)
        """
        unique_id = str(uuid.uuid4())
        local_filename = f"{unique_id}.{extension}"
        minio_object_name = f"tts/{local_filename}"

        return local_filename, minio_object_name

    @staticmethod
    def get_local_path(filename: str) -> str:
        """
        Get full local path for a filename.

        Args:
            filename: Filename without path

        Returns:
            str: Full local path
        """
        return os.path.join(settings.TEMP_DIR, filename)

    @staticmethod
    def apply_speed_adjustment(
        input_path: str,
        output_path: str,
        speed: float = 1.0
    ) -> None:
        """
        Apply speed adjustment to audio file using pydub.

        Args:
            input_path: Path to input audio file
            output_path: Path to save adjusted audio
            speed: Speed multiplier (0.5 = half speed, 2.0 = double speed)

        Raises:
            RuntimeError: If speed adjustment fails
        """
        try:
            if speed == 1.0:
                # No adjustment needed, just copy
                import shutil
                shutil.copy(input_path, output_path)
                return

            logger.info(f"Applying speed adjustment: {speed}x")

            # Load audio
            audio = AudioSegment.from_wav(input_path)

            # Apply speed change
            # Speed up = increase frame rate, slow down = decrease frame rate
            new_sample_rate = int(audio.frame_rate * speed)

            # Change frame rate (speed adjustment)
            speed_audio = audio._spawn(
                audio.raw_data,
                overrides={'frame_rate': new_sample_rate}
            )

            # Resample back to original rate to maintain pitch
            adjusted_audio = speed_audio.set_frame_rate(audio.frame_rate)

            # Export
            adjusted_audio.export(output_path, format="wav")

            logger.info(f"Speed adjustment applied successfully")

        except Exception as e:
            logger.error(f"Speed adjustment failed: {e}")
            raise RuntimeError(f"Speed adjustment failed: {e}")

    @staticmethod
    def get_audio_duration(file_path: str) -> int:
        """
        Get audio file duration in milliseconds.

        Args:
            file_path: Path to audio file

        Returns:
            int: Duration in milliseconds

        Raises:
            RuntimeError: If duration extraction fails
        """
        try:
            audio = AudioSegment.from_wav(file_path)
            duration_ms = len(audio)
            logger.info(f"Audio duration: {duration_ms}ms ({duration_ms/1000:.2f}s)")
            return duration_ms

        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            # Return 0 if unable to determine duration
            return 0

    @staticmethod
    async def store_audio(local_path: str, object_name: str) -> str:
        """
        Upload audio file to MinIO and return presigned URL.

        Args:
            local_path: Local path to audio file
            object_name: Object name in MinIO bucket

        Returns:
            str: Presigned URL to download the audio

        Raises:
            Exception: If upload or URL generation fails
        """
        try:
            logger.info(f"Storing audio to MinIO: {object_name}")

            # Upload to MinIO
            minio_client.upload_file(local_path, object_name)

            # Generate presigned URL
            url = minio_client.get_presigned_url(object_name)

            logger.info(f"Audio stored successfully, URL generated")
            return url

        except Exception as e:
            logger.error(f"Failed to store audio: {e}")
            raise

    @staticmethod
    def cleanup_local_file(file_path: str) -> None:
        """
        Delete a local file.

        Args:
            file_path: Path to file to delete
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up local file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")

    @staticmethod
    def cleanup_local_files(*file_paths: str) -> None:
        """
        Delete multiple local files.

        Args:
            *file_paths: Variable number of file paths to delete
        """
        for file_path in file_paths:
            AudioStorageService.cleanup_local_file(file_path)
