"""
Rasa NLU Engine Wrapper
Provides unified interface for Rasa-based intent and entity detection
"""

import asyncio
import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class RasaNLUEngine:
    """
    Async wrapper for Rasa NLU
    Handles intent classification and entity extraction
    """

    def __init__(self):
        self.model_path = "/models/nlu/rasa"
        self.config_path = "/app/rasa_config/config.yml"
        self.domain_path = "/app/rasa_config/domain.yml"
        self.training_data_path = "/app/rasa_config/data"
        self.interpreter = None
        self.is_loaded = False
        self._lock = asyncio.Lock()

    async def load_model(self) -> bool:
        """
        Load trained Rasa model

        Returns:
            bool: True if model loaded successfully
        """
        async with self._lock:
            try:
                # Check if model exists
                if not os.path.exists(self.model_path):
                    logger.warning(f"No trained model found at {self.model_path}")
                    logger.info("Please run training first or model will use fallback")
                    self.is_loaded = False
                    return False

                # Lazy import to avoid import errors if Rasa not installed
                from rasa.model import get_latest_model
                from rasa.nlu.model import Interpreter

                # Get latest model in directory
                model_file = get_latest_model(self.model_path)

                if not model_file:
                    logger.warning("No model file found in model directory")
                    self.is_loaded = False
                    return False

                # Load in thread pool (Rasa is sync)
                loop = asyncio.get_event_loop()
                self.interpreter = await loop.run_in_executor(
                    None,
                    Interpreter.load,
                    model_file
                )

                self.is_loaded = True
                logger.info(f"✅ Rasa model loaded successfully from {model_file}")
                return True

            except ImportError:
                logger.error("Rasa not installed. Please install: pip install rasa")
                self.is_loaded = False
                return False
            except Exception as e:
                logger.error(f"❌ Failed to load Rasa model: {e}", exc_info=True)
                self.is_loaded = False
                return False

    async def train(self, output_path: Optional[str] = None) -> bool:
        """
        Train Rasa NLU model

        Args:
            output_path: Optional custom output path for trained model

        Returns:
            bool: True if training successful
        """
        async with self._lock:
            try:
                from rasa.model_training import train_nlu

                logger.info("🚀 Starting Rasa NLU training...")
                logger.info(f"Config: {self.config_path}")
                logger.info(f"Training data: {self.training_data_path}")

                output = output_path or self.model_path

                # Ensure output directory exists
                os.makedirs(output, exist_ok=True)

                # Run training in thread pool (Rasa is sync)
                loop = asyncio.get_event_loop()
                model_path = await loop.run_in_executor(
                    None,
                    train_nlu,
                    self.config_path,
                    self.training_data_path,
                    output,
                    None,  # fixed_model_name
                    None,  # persist_nlu_training_data
                    None,  # additional_arguments
                    self.domain_path
                )

                if model_path:
                    logger.info(f"✅ Training completed successfully!")
                    logger.info(f"Model saved to: {model_path}")

                    # Load the newly trained model
                    logger.info("Loading newly trained model...")
                    await self.load_model()

                    return True
                else:
                    logger.error("❌ Training failed - no model produced")
                    return False

            except ImportError:
                logger.error("Rasa not installed. Please install: pip install rasa")
                return False
            except Exception as e:
                logger.error(f"❌ Training failed: {e}", exc_info=True)
                return False

    async def parse(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse text for intent and entities

        Args:
            text: User input text
            context: Optional conversation context

        Returns:
            Dictionary containing:
                - intent: {"name": str, "confidence": float}
                - entities: [{"entity_type": str, "value": str, ...}]
                - sentiment: {"label": str, "score": float}
        """
        if not self.is_loaded or not self.interpreter:
            logger.warning("Model not loaded, using fallback classification")
            return self._fallback_parse(text)

        try:
            # Run parsing in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.interpreter.parse,
                text
            )

            # Extract intent
            intent = result.get("intent", {})
            intent_name = intent.get("name", "out_of_scope")
            intent_confidence = intent.get("confidence", 0.0)

            # Extract entities
            entities = []
            for ent in result.get("entities", []):
                entities.append({
                    "entity_type": ent.get("entity"),
                    "value": ent.get("value"),
                    "confidence": ent.get("confidence_entity", 1.0),
                    "start_char": ent.get("start"),
                    "end_char": ent.get("end"),
                    "extractor": ent.get("extractor", "DIETClassifier")
                })

            # Sentiment analysis (placeholder - can add transformer-based sentiment later)
            sentiment = self._analyze_sentiment(text)

            logger.debug(
                f"Parsed: '{text}' -> Intent: {intent_name} ({intent_confidence:.2f}), "
                f"Entities: {len(entities)}"
            )

            return {
                "intent": {
                    "name": intent_name,
                    "confidence": intent_confidence
                },
                "entities": entities,
                "sentiment": sentiment,
                "intent_ranking": result.get("intent_ranking", [])[:5]
            }

        except Exception as e:
            logger.error(f"❌ Parsing failed: {e}", exc_info=True)
            return self._fallback_parse(text)

    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """
        Fallback rule-based parsing when Rasa model unavailable
        Uses keyword matching similar to Phase 1
        """
        text_lower = text.lower()

        # Simple keyword-based intent detection
        intent_name = "out_of_scope"
        confidence = 0.5

        if any(word in text_lower for word in ["hello", "hi", "hey", "greet"]):
            intent_name = "greet"
            confidence = 0.9
        elif any(word in text_lower for word in ["bye", "goodbye", "see you"]):
            intent_name = "goodbye"
            confidence = 0.9
        elif any(word in text_lower for word in ["balance", "money", "account"]):
            intent_name = "check_balance"
            confidence = 0.7
        elif any(word in text_lower for word in ["transfer", "send", "pay"]):
            intent_name = "transfer_money"
            confidence = 0.7
        elif any(word in text_lower for word in ["help", "assist"]):
            intent_name = "help"
            confidence = 0.8
        elif any(word in text_lower for word in ["cancel", "stop", "nevermind"]):
            intent_name = "cancel"
            confidence = 0.8

        # Simple entity extraction
        entities = self._extract_entities_fallback(text)

        # Simple sentiment
        sentiment = self._analyze_sentiment(text)

        return {
            "intent": {
                "name": intent_name,
                "confidence": confidence
            },
            "entities": entities,
            "sentiment": sentiment,
            "intent_ranking": []
        }

    def _extract_entities_fallback(self, text: str) -> List[Dict[str, Any]]:
        """Fallback entity extraction using regex"""
        import re

        entities = []

        # Amount patterns: $500, 500 dollars, etc.
        amount_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:dollars?|bucks?|usd)',
        ]

        for pattern in amount_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(1).replace(',', '')
                entities.append({
                    "entity_type": "amount",
                    "value": value,
                    "confidence": 0.9,
                    "start_char": match.start(),
                    "end_char": match.end(),
                    "extractor": "regex_fallback"
                })

        # Account type patterns
        account_types = ["checking", "savings", "credit", "debit"]
        for acc_type in account_types:
            if acc_type in text.lower():
                start = text.lower().index(acc_type)
                entities.append({
                    "entity_type": "account_type",
                    "value": acc_type,
                    "confidence": 0.9,
                    "start_char": start,
                    "end_char": start + len(acc_type),
                    "extractor": "regex_fallback"
                })

        return entities

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Simple keyword-based sentiment analysis
        Can be enhanced with transformer models later
        """
        text_lower = text.lower()

        positive_words = [
            "thank", "thanks", "great", "good", "excellent",
            "love", "perfect", "happy", "wonderful"
        ]
        negative_words = [
            "bad", "terrible", "awful", "hate", "worst",
            "useless", "frustrated", "angry", "disappointed"
        ]

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return {"label": "positive", "score": 0.7 + (positive_count * 0.1)}
        elif negative_count > positive_count:
            return {"label": "negative", "score": 0.7 + (negative_count * 0.1)}
        else:
            return {"label": "neutral", "score": 0.5}

    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        return {
            "is_loaded": self.is_loaded,
            "model_path": self.model_path,
            "config_path": self.config_path,
            "training_data_path": self.training_data_path,
            "model_exists": os.path.exists(self.model_path)
        }
