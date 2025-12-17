"""File cleanup utilities for temporary file management."""

import os
import time
import logging
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)


def cleanup_old_files(directory: str, max_age_hours: int = 1) -> int:
    """
    Remove files older than specified age from directory.

    Args:
        directory: Directory to clean
        max_age_hours: Maximum file age in hours

    Returns:
        int: Number of files deleted
    """
    try:
        if not os.path.exists(directory):
            return 0

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0

        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)

            # Skip directories
            if os.path.isdir(file_path):
                continue

            # Check file age
            file_age = current_time - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.debug(f"Deleted old file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old files from {directory}")

        return deleted_count

    except Exception as e:
        logger.error(f"Cleanup failed for {directory}: {e}")
        return 0


def cleanup_temp_directory() -> int:
    """
    Cleanup the temporary upload directory.

    Returns:
        int: Number of files deleted
    """
    return cleanup_old_files(settings.TEMP_DIR, max_age_hours=1)
