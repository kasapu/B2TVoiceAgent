"""
Intent Classification using spaCy TextCategorizer
Phase 1: Basic rule-based + simple ML classifier
"""

import spacy
from spacy.training import Example
import random
from typing import Dict, Any, List, Tuple
import logging
import os
import asyncpg

logger = logging.getLogger(__name__)


class IntentClassifier:
    """Intent classification using spaCy"""

    def __init__(self):
        self.nlp = None
        self.is_trained = False
        self.intents = []
        self.db_url = os.getenv("DATABASE_URL", "postgresql://ocpuser:ocppassword@postgres:5432/ocplatform")

    async def load_or_train(self):
        """Load existing model or train new one"""
        model_path = "/models/nlu/intent_classifier"

        # Try to load existing model
        if os.path.exists(model_path):
            try:
                logger.info(f"Loading model from {model_path}")
                self.nlp = spacy.load(model_path)
                self.is_trained = True
                logger.info("Model loaded successfully")
                return
            except Exception as e:
                logger.warning(f"Failed to load model: {e}")

        # No model found, train new one
        logger.info("No pre-trained model found, training new model...")
        await self.train()

    async def train(self):
        """
        Train intent classification model on data from database

        Fetches training examples from PostgreSQL and trains spaCy model
        """
        logger.info("Fetching training data from database...")

        # Get training data
        training_data = await self._fetch_training_data()

        if not training_data:
            logger.warning("No training data found, using rule-based fallback")
            self.nlp = spacy.blank("en")
            self.is_trained = False
            return

        logger.info(f"Training on {len(training_data)} examples")

        # Create blank English model
        self.nlp = spacy.blank("en")

        # Add text categorizer
        if "textcat" not in self.nlp.pipe_names:
            textcat = self.nlp.add_pipe("textcat", last=True)
        else:
            textcat = self.nlp.get_pipe("textcat")

        # Add labels
        for intent, examples in training_data.items():
            textcat.add_label(intent)
            self.intents.append(intent)

        # Prepare training examples
        train_examples = []
        for intent, examples in training_data.items():
            for text in examples:
                # Create labels dict (one-hot encoding)
                cats = {label: (label == intent) for label in self.intents}
                doc = self.nlp.make_doc(text)
                train_examples.append(Example.from_dict(doc, {"cats": cats}))

        # Train
        logger.info("Training model...")
        optimizer = self.nlp.initialize()

        # Training loop
        n_iter = 10
        for i in range(n_iter):
            random.shuffle(train_examples)
            losses = {}

            # Batch training
            for batch in spacy.util.minibatch(train_examples, size=8):
                self.nlp.update(batch, sgd=optimizer, losses=losses)

            logger.info(f"Iteration {i+1}/{n_iter}, Loss: {losses.get('textcat', 0):.4f}")

        self.is_trained = True
        logger.info("Training completed!")

        # Save model
        model_path = "/models/nlu/intent_classifier"
        try:
            os.makedirs(model_path, exist_ok=True)
            self.nlp.to_disk(model_path)
            logger.info(f"Model saved to {model_path}")
        except Exception as e:
            logger.warning(f"Failed to save model: {e}")

    async def classify(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Classify intent from text

        Args:
            text: User input text
            context: Optional context for disambiguation

        Returns:
            Dictionary with intent, confidence, entities, sentiment
        """
        if not self.nlp or not self.is_trained:
            # Use simple rule-based fallback
            return self._rule_based_classify(text)

        # Use trained model
        doc = self.nlp(text)

        # Get scores from textcat
        scores = doc.cats

        # Find highest scoring intent
        if scores:
            intent_name = max(scores, key=scores.get)
            confidence = scores[intent_name]
        else:
            intent_name = "out_of_scope"
            confidence = 0.5

        # Simple entity extraction (Phase 2: will use spaCy NER)
        entities = self._extract_entities(text)

        # Simple sentiment (Phase 2: will use sentiment model)
        sentiment = self._analyze_sentiment(text)

        return {
            "intent": {
                "name": intent_name,
                "confidence": confidence
            },
            "entities": entities,
            "sentiment": sentiment
        }

    def _rule_based_classify(self, text: str) -> Dict[str, Any]:
        """
        Simple keyword-based classification fallback

        Args:
            text: User input text

        Returns:
            Classification result
        """
        text_lower = text.lower()

        # Keyword mapping
        rules = {
            "greet": ["hello", "hi", "hey", "good morning", "good afternoon"],
            "goodbye": ["bye", "goodbye", "see you", "farewell"],
            "check_balance": ["balance", "money", "account", "how much"],
            "transfer_money": ["transfer", "send", "pay", "wire"],
            "help": ["help", "assist", "support", "what can you do"],
            "cancel": ["cancel", "stop", "nevermind", "forget it"]
        }

        # Check each rule
        for intent, keywords in rules.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return {
                        "intent": {
                            "name": intent,
                            "confidence": 0.75
                        },
                        "entities": [],
                        "sentiment": {"label": "neutral", "score": 0.5}
                    }

        # No match
        return {
            "intent": {
                "name": "out_of_scope",
                "confidence": 0.5
            },
            "entities": [],
            "sentiment": {"label": "neutral", "score": 0.5}
        }

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text

        Phase 1: Simple regex patterns
        Phase 2: Will use spaCy NER
        """
        import re

        entities = []

        # Extract amounts (e.g., $500, 500 dollars)
        amount_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',  # $500, $1,000.00
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*dollars?',  # 500 dollars
        ]

        for pattern in amount_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append({
                    "entity_type": "amount",
                    "value": match.group(1).replace(',', ''),
                    "confidence": 0.9,
                    "start_char": match.start(),
                    "end_char": match.end()
                })

        # Extract account types
        account_patterns = ["savings", "checking", "credit", "debit"]
        for account_type in account_patterns:
            if account_type in text.lower():
                pos = text.lower().index(account_type)
                entities.append({
                    "entity_type": "account_type",
                    "value": account_type,
                    "confidence": 0.85,
                    "start_char": pos,
                    "end_char": pos + len(account_type)
                })

        return entities

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text

        Phase 1: Simple keyword-based
        Phase 2: Will use sentiment model
        """
        text_lower = text.lower()

        # Positive words
        positive_words = ["thank", "thanks", "great", "good", "excellent", "love", "perfect"]
        # Negative words
        negative_words = ["bad", "terrible", "awful", "hate", "worst", "useless", "frustrated", "angry"]

        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        if pos_count > neg_count:
            return {"label": "positive", "score": 0.7}
        elif neg_count > pos_count:
            return {"label": "negative", "score": 0.7}
        else:
            return {"label": "neutral", "score": 0.6}

    async def _fetch_training_data(self) -> Dict[str, List[str]]:
        """
        Fetch training examples from PostgreSQL database

        Returns:
            Dictionary mapping intent names to lists of example texts
        """
        try:
            # Convert asyncpg URL
            db_url = self.db_url.replace("postgresql+asyncpg://", "postgresql://")

            conn = await asyncpg.connect(db_url)

            # Fetch all intents and their examples
            rows = await conn.fetch("""
                SELECT i.intent_name, te.example_text
                FROM intents i
                JOIN training_examples te ON i.intent_id = te.intent_id
                WHERE i.is_active = TRUE
                ORDER BY i.intent_name, te.example_id
            """)

            await conn.close()

            # Group by intent
            training_data = {}
            for row in rows:
                intent_name = row['intent_name']
                example_text = row['example_text']

                if intent_name not in training_data:
                    training_data[intent_name] = []

                training_data[intent_name].append(example_text)

            logger.info(f"Fetched {len(training_data)} intents with training examples")

            return training_data

        except Exception as e:
            logger.error(f"Failed to fetch training data: {e}")
            return {}

    def get_intents(self) -> List[str]:
        """Get list of supported intents"""
        if self.is_trained and self.nlp and "textcat" in self.nlp.pipe_names:
            textcat = self.nlp.get_pipe("textcat")
            return list(textcat.labels)

        # Fallback to hardcoded list
        return ["greet", "goodbye", "check_balance", "transfer_money", "help", "cancel", "out_of_scope"]
