"""
OCP Platform - Orchestrator Service
Main FastAPI application for conversation orchestration
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Optional
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, get_db
from app.core.redis_client import redis_client
from app.api import conversations, health, flows, voice

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting OCP Orchestrator Service...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")

    # Test database connection
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✓ Database connection successful")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        raise

    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("✓ Redis connection successful")
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")
        raise

    logger.info("Orchestrator service started successfully!")

    yield

    # Shutdown
    logger.info("Shutting down Orchestrator Service...")
    await engine.dispose()
    await redis_client.close()
    logger.info("Orchestrator service stopped")


# Create FastAPI app
app = FastAPI(
    title="OCP Orchestrator API",
    description="Central orchestration service for conversational AI",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(conversations.router, prefix="/v1/conversations", tags=["Conversations"])
app.include_router(flows.router, prefix="/v1/flows", tags=["Flows"])
app.include_router(voice.router, prefix="/api/v1", tags=["Voice"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OCP Orchestrator",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.RELOAD
    )
