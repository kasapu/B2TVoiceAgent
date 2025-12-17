"""FastAPI application for TTS (Text-to-Speech) service."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.models.schemas import SynthesizeRequest, SynthesizeResponse, HealthResponse, ErrorResponse
from app.services.synthesis import SynthesisService

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
    logger.info(f"TTS Model: {settings.TTS_MODEL}")
    logger.info(f"Device: {settings.DEVICE}")
    logger.info(f"MinIO Endpoint: {settings.MINIO_ENDPOINT}")
    logger.info("=" * 50)

    # Load TTS model on startup
    from app.models.tts_model import model_manager
    try:
        logger.info("Loading TTS model...")
        model_manager.load_model()
        logger.info(f"Model loaded successfully on {model_manager.get_device()}")
        logger.info(f"Available voices: {model_manager.get_available_voices()}")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    # Initialize MinIO client
    from app.core.minio_client import minio_client
    try:
        logger.info("Initializing MinIO client...")
        # Client is initialized in constructor
        logger.info("MinIO client ready")
    except Exception as e:
        logger.error(f"Failed to initialize MinIO: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down TTS service...")


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
        "model": settings.TTS_MODEL,
        "endpoints": {
            "synthesize": "POST /synthesize",
            "health": "GET /health",
            "voices": "GET /voices",
            "docs": "GET /docs"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns detailed information about service status, model, device, and MinIO connection.
    """
    try:
        health_data = SynthesisService.get_service_health()

        return HealthResponse(
            status=health_data.get("status", "unknown"),
            service=settings.SERVICE_NAME,
            version=settings.VERSION,
            model=health_data.get("model", settings.TTS_MODEL),
            device=health_data.get("device", "unknown"),
            device_info=health_data.get("device_info", {}),
            minio_connected=health_data.get("minio_connected", False),
            available_voices=health_data.get("available_voices", [])
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/voices", tags=["Info"])
async def list_voices():
    """
    List available voice IDs.

    Returns a list of voice/speaker IDs that can be used with the synthesize endpoint.
    """
    try:
        from app.models.tts_model import model_manager

        voices = model_manager.get_available_voices()

        return {
            "voices": voices,
            "count": len(voices),
            "multi_speaker": model_manager.is_multi_speaker()
        }
    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve voice list")


@app.post(
    "/synthesize",
    response_model=SynthesizeResponse,
    responses={
        200: {"description": "Synthesis successful"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        500: {"model": ErrorResponse, "description": "Synthesis failed"}
    },
    tags=["Synthesis"]
)
async def synthesize_speech(request: SynthesizeRequest):
    """
    Synthesize speech from text.

    Convert text to natural-sounding speech and return a presigned URL to download
    the generated audio file. The audio is stored in MinIO S3-compatible storage
    with a 24-hour expiry on the download link.

    Example:
        ```bash
        curl -X POST "http://localhost:8003/synthesize" \\
          -H "Content-Type: application/json" \\
          -d '{
            "text": "Hello, how can I help you today?",
            "voice": "default",
            "speed": 1.0
          }'
        ```

    Args:
        request: Synthesis request containing text and optional parameters

    Returns:
        SynthesizeResponse: Response with audio URL and metadata
    """
    try:
        logger.info(f"Received synthesis request")
        logger.info(f"Text length: {len(request.text)} characters")

        # Perform synthesis
        result = await SynthesisService.synthesize_speech(request)

        return result

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Synthesis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )
