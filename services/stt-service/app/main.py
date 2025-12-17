"""FastAPI application for STT (Speech-to-Text) service."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from app.core.config import settings
from app.models.schemas import TranscribeResponse, HealthResponse, ErrorResponse
from app.services.transcription import TranscriptionService
from app.utils.file_cleanup import cleanup_temp_directory

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events."""
    # Startup
    logger.info("=" * 50)
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.VERSION}")
    logger.info(f"Whisper Model: {settings.WHISPER_MODEL}")
    logger.info(f"Device: {settings.DEVICE}, Compute Type: {settings.COMPUTE_TYPE}")
    logger.info("=" * 50)

    # Load model on startup
    from app.models.whisper_model import model_manager
    try:
        logger.info("Loading Whisper model...")
        model_manager.load_model()
        logger.info(f"Model loaded successfully on {model_manager.get_device()}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    # Cleanup old temp files
    cleanup_temp_directory()

    yield

    # Shutdown
    logger.info("Shutting down STT service...")
    cleanup_temp_directory()


# Create FastAPI app
app = FastAPI(
    title=settings.SERVICE_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "model": settings.WHISPER_MODEL,
        "endpoints": {
            "transcribe": "POST /transcribe",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns detailed information about service status, model, and device.
    """
    try:
        health_data = TranscriptionService.get_service_health()

        return HealthResponse(
            status=health_data.get("status", "unknown"),
            service=settings.SERVICE_NAME,
            version=settings.VERSION,
            model=health_data.get("model", settings.WHISPER_MODEL),
            device=health_data.get("device", "unknown"),
            device_info=health_data.get("device_info", {})
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.post(
    "/transcribe",
    response_model=TranscribeResponse,
    responses={
        200: {"description": "Transcription successful"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        413: {"model": ErrorResponse, "description": "File too large"},
        500: {"model": ErrorResponse, "description": "Transcription failed"}
    },
    tags=["Transcription"]
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: Optional[str] = Form(default=None, description="Language code (e.g., 'en', 'es', 'fr')"),
    task: str = Form(default="transcribe", description="Task: 'transcribe' or 'translate'"),
    beam_size: int = Form(default=5, description="Beam size for decoding (1-10)"),
    temperature: float = Form(default=0.0, description="Temperature for sampling (0.0-1.0)")
):
    """
    Transcribe audio file to text.

    Upload an audio file and receive the transcribed text along with metadata
    including detected language, duration, and optional segments with timestamps.

    Supported formats: WAV, MP3, M4A, FLAC, OGG, WEBM
    Maximum file size: 25MB

    Example:
        ```bash
        curl -X POST "http://localhost:8002/transcribe" \\
          -F "file=@audio.wav" \\
          -F "language=en" \\
          -F "task=transcribe"
        ```
    """
    try:
        logger.info(f"Received transcription request for file: {file.filename}")

        # Validate parameters
        if task not in ["transcribe", "translate"]:
            raise HTTPException(status_code=400, detail="Task must be 'transcribe' or 'translate'")

        if beam_size < 1 or beam_size > 10:
            raise HTTPException(status_code=400, detail="Beam size must be between 1 and 10")

        if temperature < 0.0 or temperature > 1.0:
            raise HTTPException(status_code=400, detail="Temperature must be between 0.0 and 1.0")

        # Perform transcription
        result = await TranscriptionService.transcribe_audio(
            file=file,
            language=language,
            task=task,
            beam_size=beam_size,
            temperature=temperature
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@app.get("/cleanup", tags=["Maintenance"])
async def cleanup_files():
    """
    Manually trigger cleanup of old temporary files.

    Removes files older than 1 hour from the temporary directory.
    """
    try:
        deleted_count = cleanup_temp_directory()
        return {
            "status": "success",
            "message": f"Cleaned up {deleted_count} old files"
        }
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )
