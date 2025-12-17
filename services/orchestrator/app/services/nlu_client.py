"""
NLU Service Client
Communicates with the NLU microservice for intent and entity detection
"""

import httpx
from typing import Dict, Any, List, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class NLUClient:
    """Client for communicating with NLU service"""

    def __init__(self):
        self.base_url = settings.NLU_SERVICE_URL
        self.timeout = 5.0

    async def parse(
        self,
        text: str,
        language: str = "en-US",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse text for intent and entities

        Args:
            text: User input text
            language: Language code
            context: Optional context for disambiguation

        Returns:
            Dictionary with:
            - intent: {name, confidence}
            - entities: [{entity_type, value, confidence}]
            - sentiment: {label, score}
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/parse",
                    json={
                        "text": text,
                        "language": language,
                        "context": context or {}
                    },
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"NLU service error: {response.status_code} - {response.text}")
                    return self._fallback_intent(text)

        except httpx.TimeoutException:
            logger.error(f"NLU service timeout for text: {text}")
            return self._fallback_intent(text)

        except Exception as e:
            logger.error(f"NLU service error: {e}")
            return self._fallback_intent(text)

    def _fallback_intent(self, text: str) -> Dict[str, Any]:
        """
        Simple rule-based fallback when NLU service is unavailable

        Args:
            text: User input text

        Returns:
            Basic intent detection result
        """
        text_lower = text.lower()

        # Simple keyword matching
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

        else:
            intent_name = "out_of_scope"
            confidence = 0.5

        logger.info(f"Fallback intent detection: {intent_name} ({confidence})")

        return {
            "intent": {
                "name": intent_name,
                "confidence": confidence
            },
            "entities": [],
            "sentiment": {
                "label": "neutral",
                "score": 0.5
            }
        }
