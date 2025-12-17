"""Audio file processing utilities using FFmpeg."""

import os
import logging
import uuid
import subprocess
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Handles audio file upload, conversion, and processing."""

    @staticmethod
    async def save_upload(file: UploadFile, max_size_mb: Optional[int] = None) -> str:
        """
        Save uploaded file to temporary directory.

        Args:
            file: Uploaded file from FastAPI
            max_size_mb: Maximum file size in MB (uses settings default if None)

        Returns:
            str: Path to saved file

        Raises:
            HTTPException: If file is too large or save fails
        """
        max_size = (max_size_mb or settings.MAX_FILE_SIZE_MB) * 1024 * 1024

        try:
            # Generate unique filename
            file_ext = Path(file.filename).suffix if file.filename else ".wav"
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(settings.TEMP_DIR, unique_filename)

            # Read and save file
            content = await file.read()

            # Check file size
            if len(content) > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
                )

            with open(file_path, "wb") as f:
                f.write(content)

            logger.info(f"Saved uploaded file to: {file_path} ({len(content)} bytes)")
            return file_path

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    @staticmethod
    def convert_to_wav(
        input_path: str,
        sample_rate: Optional[int] = None,
        channels: int = 1
    ) -> str:
        """
        Convert audio file to WAV format using FFmpeg.

        Args:
            input_path: Path to input audio file
            sample_rate: Target sample rate (uses settings default if None)
            channels: Number of audio channels (1=mono, 2=stereo)

        Returns:
            str: Path to converted WAV file

        Raises:
            RuntimeError: If conversion fails
        """
        sample_rate = sample_rate or settings.SAMPLE_RATE

        try:
            # Generate output path
            output_path = input_path.rsplit(".", 1)[0] + "_converted.wav"

            # FFmpeg command
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-ar", str(sample_rate),
                "-ac", str(channels),
                "-y",  # Overwrite output file
                output_path
            ]

            logger.info(f"Converting audio with FFmpeg: {' '.join(cmd)}")

            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info(f"Audio converted successfully to: {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg conversion failed: {e.stderr}")
            raise RuntimeError(f"Audio conversion failed: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error during conversion: {e}")
            raise RuntimeError(f"Audio conversion failed: {str(e)}")

    @staticmethod
    def get_audio_duration(file_path: str) -> float:
        """
        Get audio file duration using FFprobe.

        Args:
            file_path: Path to audio file

        Returns:
            float: Duration in seconds

        Raises:
            RuntimeError: If duration extraction fails
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            duration = float(result.stdout.strip())
            logger.info(f"Audio duration: {duration:.2f} seconds")
            return duration

        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            # Return 0 if unable to determine duration
            return 0.0

    @staticmethod
    def cleanup_file(file_path: str) -> None:
        """
        Delete a file from filesystem.

        Args:
            file_path: Path to file to delete
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")

    @staticmethod
    def cleanup_files(*file_paths: str) -> None:
        """
        Delete multiple files from filesystem.

        Args:
            *file_paths: Variable number of file paths to delete
        """
        for file_path in file_paths:
            AudioProcessor.cleanup_file(file_path)

    @staticmethod
    def validate_audio_format(filename: str) -> bool:
        """
        Validate if file format is supported.

        Args:
            filename: Name of the file

        Returns:
            bool: True if format is supported
        """
        if not filename:
            return False

        file_ext = Path(filename).suffix.lower().lstrip(".")
        return file_ext in settings.SUPPORTED_FORMATS
