"""MinIO client for audio file storage."""

import logging
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from app.core.config import settings

logger = logging.getLogger(__name__)


class MinIOClient:
    """
    MinIO S3-compatible storage client for TTS audio files.
    Singleton pattern to reuse connection.
    """

    _instance = None
    _client = None

    def __new__(cls):
        """Singleton pattern - only one instance allowed."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize MinIO client (only once)."""
        if self._client is None:
            self._initialize_client()

    def _initialize_client(self) -> None:
        """Create and configure MinIO client."""
        try:
            logger.info(f"Connecting to MinIO at {settings.MINIO_ENDPOINT}")

            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )

            # Ensure bucket exists
            self._ensure_bucket()

            logger.info("MinIO client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            raise RuntimeError(f"MinIO initialization failed: {e}")

    def _ensure_bucket(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            bucket_exists = self._client.bucket_exists(settings.MINIO_BUCKET)

            if not bucket_exists:
                logger.info(f"Creating bucket: {settings.MINIO_BUCKET}")
                self._client.make_bucket(settings.MINIO_BUCKET)
                logger.info(f"Bucket '{settings.MINIO_BUCKET}' created successfully")
            else:
                logger.info(f"Bucket '{settings.MINIO_BUCKET}' already exists")

        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise

    def upload_file(self, file_path: str, object_name: str) -> str:
        """
        Upload a file to MinIO.

        Args:
            file_path: Local path to file
            object_name: Object name in bucket (e.g., 'tts/uuid.wav')

        Returns:
            str: Object name in bucket

        Raises:
            Exception: If upload fails
        """
        try:
            logger.info(f"Uploading {file_path} to MinIO as {object_name}")

            self._client.fput_object(
                settings.MINIO_BUCKET,
                object_name,
                file_path,
                content_type="audio/wav"
            )

            logger.info(f"File uploaded successfully: {object_name}")
            return object_name

        except S3Error as e:
            logger.error(f"Failed to upload file to MinIO: {e}")
            raise Exception(f"MinIO upload failed: {e}")

    def get_presigned_url(self, object_name: str, expiry_hours: int = None) -> str:
        """
        Generate a presigned URL for downloading the file.

        Args:
            object_name: Object name in bucket
            expiry_hours: URL expiry time in hours (uses settings default if None)

        Returns:
            str: Presigned URL

        Raises:
            Exception: If URL generation fails
        """
        try:
            expiry = timedelta(hours=expiry_hours or settings.AUDIO_URL_EXPIRY_HOURS)

            url = self._client.presigned_get_object(
                settings.MINIO_BUCKET,
                object_name,
                expires=expiry
            )

            logger.info(f"Generated presigned URL for {object_name} (expires in {expiry.total_seconds()/3600}h)")
            return url

        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise Exception(f"Presigned URL generation failed: {e}")

    def delete_file(self, object_name: str) -> None:
        """
        Delete a file from MinIO.

        Args:
            object_name: Object name in bucket
        """
        try:
            self._client.remove_object(settings.MINIO_BUCKET, object_name)
            logger.info(f"Deleted file from MinIO: {object_name}")
        except S3Error as e:
            logger.warning(f"Failed to delete file {object_name}: {e}")

    def list_files(self, prefix: str = "") -> list:
        """
        List files in bucket with optional prefix.

        Args:
            prefix: Object name prefix filter

        Returns:
            list: List of object names
        """
        try:
            objects = self._client.list_objects(
                settings.MINIO_BUCKET,
                prefix=prefix,
                recursive=True
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Failed to list files: {e}")
            return []


# Global MinIO client instance
minio_client = MinIOClient()
