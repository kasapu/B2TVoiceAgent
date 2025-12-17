"""
SIP Gateway Service - Main Application
FastAPI application for SIP-to-Voice Connector bridging
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.schemas import (
    HealthCheckResponse,
    ActiveCallsResponse,
    CallMetrics
)
from app.services.call_router import CallRouter

logger = get_logger(__name__)

# Global call router instance
call_router: CallRouter = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager

    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting SIP Gateway service")
    global call_router

    try:
        # Initialize call router
        call_router = CallRouter()

        # Start call router
        success = await call_router.start()
        if not success:
            logger.error("Failed to start call router")
            raise RuntimeError("Failed to start call router")

        logger.info(f"{settings.SERVICE_NAME} v{settings.VERSION} started successfully")

        yield

    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down SIP Gateway service")
        if call_router:
            await call_router.stop()
        logger.info("SIP Gateway service stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint

    Returns service health status
    """
    global call_router

    if not call_router:
        raise HTTPException(status_code=503, detail="Call router not initialized")

    # Check FreeSWITCH connection
    freeswitch_connected = call_router.esl_handler.is_connected

    # Check if we have any active calls (indicates voice connector is working)
    active_calls = len(call_router.active_bridges)

    # Determine voice connector status
    voice_connector_connected = False
    if active_calls > 0:
        # Check if at least one bridge has active voice connector
        for bridge in call_router.active_bridges.values():
            if bridge.voice_connector.is_connected:
                voice_connector_connected = True
                break

    # Determine SIP trunk status
    sip_trunk_status = "registered" if freeswitch_connected else "disconnected"

    # Overall status
    status = "healthy" if freeswitch_connected else "degraded"

    return HealthCheckResponse(
        status=status,
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        freeswitch_connected=freeswitch_connected,
        voice_connector_connected=voice_connector_connected,
        active_calls=active_calls,
        sip_trunk_status=sip_trunk_status
    )


@app.get("/calls", response_model=ActiveCallsResponse)
async def get_active_calls():
    """
    Get active calls

    Returns list of currently active calls
    """
    global call_router

    if not call_router:
        raise HTTPException(status_code=503, detail="Call router not initialized")

    calls = call_router.get_active_calls()

    return ActiveCallsResponse(
        active_calls=len(calls),
        calls=calls
    )


@app.get("/metrics", response_model=CallMetrics)
async def get_metrics():
    """
    Get call metrics

    Returns call statistics and metrics
    """
    global call_router

    if not call_router:
        raise HTTPException(status_code=503, detail="Call router not initialized")

    metrics = call_router.get_metrics()
    return metrics


@app.get("/calls/{unique_id}")
async def get_call(unique_id: str):
    """
    Get specific call information

    Args:
        unique_id: FreeSWITCH unique call ID

    Returns:
        Call information
    """
    global call_router

    if not call_router:
        raise HTTPException(status_code=503, detail="Call router not initialized")

    bridge = call_router.get_bridge(unique_id)
    if not bridge:
        raise HTTPException(status_code=404, detail=f"Call {unique_id} not found")

    call_info = bridge.get_call_info()
    return call_info


@app.get("/freeswitch/status")
async def freeswitch_status():
    """
    Get FreeSWITCH connection status

    Returns FreeSWITCH ESL connection information
    """
    global call_router

    if not call_router:
        raise HTTPException(status_code=503, detail="Call router not initialized")

    return {
        "connected": call_router.esl_handler.is_connected,
        "host": settings.FREESWITCH_HOST,
        "port": settings.FREESWITCH_ESL_PORT
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """
    Handle uncaught exceptions

    Args:
        request: Request
        exc: Exception

    Returns:
        JSON error response
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )
