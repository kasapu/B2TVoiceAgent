"""
OCP Platform - NLU Service
Natural Language Understanding service for intent and entity detection
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import os

# Phase 2: Import Rasa NLU Engine
try:
    from rasa_nlu import RasaNLUEngine
    USE_RASA = True
    logger_init = logging.getLogger(__name__)
    logger_init.info("✅ Rasa NLU available - using Rasa engine")
except ImportError:
    USE_RASA = False
    from intent_classifier import IntentClassifier
    logger_init = logging.getLogger(__name__)
    logger_init.info("⚠️ Rasa not available - falling back to spaCy classifier")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OCP NLU Service",
    description="Natural Language Understanding for intent classification (Phase 2: Rasa NLU)",
    version="2.0.0"
)

# Initialize NLU engine (Rasa or fallback to spaCy)
nlu_engine = None


@app.on_event("startup")
async def startup_event():
    """Load NLU model on startup"""
    global nlu_engine
    logger.info("Starting NLU Service...")

    try:
        if USE_RASA:
            logger.info("🚀 Initializing Rasa NLU Engine...")
            nlu_engine = RasaNLUEngine()

            # Try to load existing model
            loaded = await nlu_engine.load_model()

            if not loaded:
                logger.warning("⚠️  No Rasa model found. Train model or using fallback parsing.")
                logger.info("💡 Run POST /train to train Rasa model")
            else:
                logger.info("✅ Rasa NLU model loaded successfully")
        else:
            logger.info("Using spaCy IntentClassifier (Phase 1 fallback)...")
            nlu_engine = IntentClassifier()
            await nlu_engine.load_or_train()
            logger.info("✓ spaCy model loaded successfully")

    except Exception as e:
        logger.error(f"❌ Failed to load NLU model: {e}", exc_info=True)
        # Don't fail startup - Rasa has fallback parsing
        if USE_RASA:
            nlu_engine = RasaNLUEngine()
        else:
            nlu_engine = IntentClassifier()

    logger.info("✅ NLU Service started successfully!")


# ============================================
# MODELS
# ============================================

class ParseRequest(BaseModel):
    """Request to parse text"""
    text: str
    language: str = "en-US"
    context: Optional[Dict[str, Any]] = {}


class Intent(BaseModel):
    """Intent detection result"""
    name: str
    confidence: float


class Entity(BaseModel):
    """Entity extraction result"""
    entity_type: str
    value: str
    confidence: float
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class Sentiment(BaseModel):
    """Sentiment analysis result"""
    label: str  # positive, neutral, negative
    score: float


class ParseResponse(BaseModel):
    """NLU parsing result"""
    intent: Intent
    entities: List[Entity] = []
    sentiment: Optional[Sentiment] = None


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OCP NLU Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if USE_RASA:
        model_loaded = nlu_engine is not None and nlu_engine.is_loaded
        model_info = await nlu_engine.get_model_info() if nlu_engine else {}

        return {
            "status": "healthy" if model_loaded else "degraded",
            "model_loaded": model_loaded,
            "model_type": "rasa_diet_classifier",
            "engine": "rasa",
            "version": "2.0.0",
            "model_info": model_info
        }
    else:
        model_loaded = nlu_engine is not None and nlu_engine.is_trained

        return {
            "status": "healthy" if model_loaded else "degraded",
            "model_loaded": model_loaded,
            "model_type": "spacy_textcat",
            "engine": "spacy",
            "version": "1.0.0"
        }


@app.post("/parse", response_model=ParseResponse)
async def parse_text(request: ParseRequest):
    """
    Parse text for intent and entities

    This is the main NLU endpoint that analyzes user input
    Phase 2: Uses Rasa NLU for enhanced accuracy
    """
    if not nlu_engine:
        raise HTTPException(status_code=503, detail="NLU model not loaded")

    try:
        logger.info(f"Parsing text: {request.text}")

        # Parse with Rasa or spaCy
        if USE_RASA:
            result = await nlu_engine.parse(request.text, request.context)
        else:
            result = await nlu_engine.classify(request.text, request.context)

        logger.info(f"Intent: {result['intent']['name']} ({result['intent']['confidence']:.2f}), "
                   f"Entities: {len(result.get('entities', []))}")

        return ParseResponse(
            intent=Intent(
                name=result["intent"]["name"],
                confidence=result["intent"]["confidence"]
            ),
            entities=[
                Entity(
                    entity_type=e["entity_type"],
                    value=e["value"],
                    confidence=e["confidence"],
                    start_char=e.get("start_char"),
                    end_char=e.get("end_char")
                )
                for e in result.get("entities", [])
            ],
            sentiment=Sentiment(
                label=result.get("sentiment", {}).get("label", "neutral"),
                score=result.get("sentiment", {}).get("score", 0.5)
            )
        )

    except Exception as e:
        logger.error(f"Error parsing text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to parse text: {str(e)}")


@app.post("/train")
async def train_model():
    """
    Trigger model training

    Phase 2: Trains Rasa NLU model on data from rasa_config/data/nlu.yml
    Use migration script first: python scripts/migrate_training_data_to_rasa.py
    """
    if not nlu_engine:
        raise HTTPException(status_code=503, detail="NLU engine not initialized")

    try:
        logger.info("🚀 Starting model training...")

        if USE_RASA:
            logger.info("Training Rasa NLU model (this may take several minutes)...")
            success = await nlu_engine.train()

            if success:
                logger.info("✅ Rasa model training completed")
                return {
                    "status": "success",
                    "message": "Rasa model trained successfully",
                    "engine": "rasa",
                    "next_steps": "Model is now loaded and ready for inference"
                }
            else:
                raise Exception("Training completed but model was not produced")
        else:
            await nlu_engine.train()
            logger.info("✅ spaCy model training completed")
            return {
                "status": "success",
                "message": "spaCy model trained successfully",
                "engine": "spacy"
            }

    except Exception as e:
        logger.error(f"❌ Training failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@app.get("/intents")
async def list_intents():
    """List all supported intents"""
    if not nlu_engine:
        raise HTTPException(status_code=503, detail="NLU engine not initialized")

    if USE_RASA:
        # Rasa intents are defined in domain.yml
        intents = [
            "greet", "goodbye", "check_balance", "transfer_money",
            "help", "cancel", "out_of_scope"
        ]
    else:
        intents = nlu_engine.get_intents()

    return {
        "intents": intents,
        "count": len(intents),
        "engine": "rasa" if USE_RASA else "spacy"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
