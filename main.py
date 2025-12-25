"""
OCP Platform - Unified Application for Replit
Combines all microservices into a single application
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import uuid
import json
import time
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import redis.asyncio as redis_async

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from enum import Enum
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SESSION_TIMEOUT_SECONDS: int = 1800
    CORS_ORIGINS: list = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()

db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
if "sslmode=" in db_url:
    db_url = db_url.split("?")[0]

engine = create_async_engine(db_url, pool_size=5, max_overflow=5, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class RedisClient:
    def __init__(self):
        self.client: Optional[redis_async.Redis] = None
        self._memory_sessions: Dict[str, Any] = {}
        self._use_memory = False

    async def connect(self):
        try:
            self.client = await redis_async.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
            self.client = None
            self._use_memory = True

    async def ping(self):
        if self._use_memory:
            return True
        if self.client:
            return await self.client.ping()
        return True

    async def close(self):
        if self.client:
            await self.client.close()

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if self._use_memory:
            return self._memory_sessions.get(session_id)
        if not self.client:
            return None
        key = f"session:{session_id}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None

    async def set_session(self, session_id: str, context: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        if self._use_memory:
            self._memory_sessions[session_id] = context
            return True
        key = f"session:{session_id}"
        ttl = ttl or settings.SESSION_TIMEOUT_SECONDS
        data = json.dumps(context)
        await self.client.setex(key, ttl, data)
        return True

    async def delete_session(self, session_id: str) -> bool:
        if self._use_memory:
            self._memory_sessions.pop(session_id, None)
            return True
        if not self.client:
            return False
        key = f"session:{session_id}"
        result = await self.client.delete(key)
        return result > 0

    async def get_ttl(self, session_id: str) -> int:
        if self._use_memory or not self.client:
            return settings.SESSION_TIMEOUT_SECONDS
        key = f"session:{session_id}"
        return await self.client.ttl(key)

redis_client = RedisClient()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class ChannelType(str, Enum):
    VOICE = "voice"
    CHAT = "chat"
    API = "api"


class InputType(str, Enum):
    TEXT = "text"
    AUDIO = "audio"


class SessionStartRequest(BaseModel):
    channel_type: ChannelType
    caller_id: Optional[str] = None
    user_id: Optional[str] = None
    initial_context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    flow_id: Optional[str] = None


class UserInputRequest(BaseModel):
    input_type: InputType
    text: Optional[str] = None
    language: str = "en-US"


class SessionEndRequest(BaseModel):
    reason: str
    user_feedback: Optional[Dict[str, Any]] = None


def extract_entities(text: str) -> list:
    """Extract entities from text (amounts, account types, etc.)"""
    entities = []
    text_lower = text.lower()
    
    amount_patterns = [
        r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'(\d+(?:,\d{3})*(?:\.\d{2})?) dollars',
        r'(\d+(?:,\d{3})*) bucks',
        r'(\d+(?:,\d{3})*(?:\.\d{2})?)'
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                entities.append({
                    "entity_type": "amount",
                    "value": amount,
                    "raw_value": match.group(0)
                })
                break
            except ValueError:
                pass
    
    account_types = {
        "checking": ["checking", "check", "chequing"],
        "savings": ["savings", "saving", "save"],
        "credit": ["credit", "credit card", "cc"],
        "money market": ["money market", "mm"],
        "investment": ["investment", "invest", "brokerage"]
    }
    
    for account_type, keywords in account_types.items():
        if any(kw in text_lower for kw in keywords):
            entities.append({
                "entity_type": "account_type",
                "value": account_type,
                "raw_value": account_type
            })
            break
    
    if "yes" in text_lower or "confirm" in text_lower or "correct" in text_lower or "sure" in text_lower or "yep" in text_lower:
        entities.append({"entity_type": "confirmation", "value": True})
    elif "no" in text_lower or "cancel" in text_lower or "wrong" in text_lower or "nope" in text_lower:
        entities.append({"entity_type": "confirmation", "value": False})
    
    return entities


def fallback_intent(text: str) -> Dict[str, Any]:
    """Enhanced NLU with more banking intents"""
    text_lower = text.lower()
    entities = extract_entities(text)
    
    if any(word in text_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        intent_name, confidence = "greet", 0.9
    elif any(word in text_lower for word in ["bye", "goodbye", "see you", "end call", "hang up", "that's all"]):
        intent_name, confidence = "goodbye", 0.9
    elif any(phrase in text_lower for phrase in ["check balance", "my balance", "account balance", "how much", "what's my balance", "whats my balance"]):
        intent_name, confidence = "check_balance", 0.85
    elif any(phrase in text_lower for phrase in ["transfer", "send money", "move money", "pay", "wire"]):
        intent_name, confidence = "transfer_money", 0.85
    elif any(phrase in text_lower for phrase in ["statement", "transaction", "history", "recent activity"]):
        intent_name, confidence = "account_statement", 0.8
    elif any(phrase in text_lower for phrase in ["card", "lost card", "stolen", "block card", "freeze"]):
        intent_name, confidence = "card_services", 0.8
    elif any(phrase in text_lower for phrase in ["speak to", "agent", "human", "representative", "person"]):
        intent_name, confidence = "transfer_agent", 0.85
    elif any(word in text_lower for word in ["help", "assist", "what can you do", "options"]):
        intent_name, confidence = "help", 0.8
    elif any(word in text_lower for word in ["yes", "correct", "confirm", "sure", "yep", "yeah", "okay", "ok"]):
        intent_name, confidence = "confirm", 0.9
    elif any(word in text_lower for word in ["no", "cancel", "stop", "nevermind", "nope", "wrong"]):
        intent_name, confidence = "deny", 0.9
    elif any(word in text_lower for word in ["checking"]):
        intent_name, confidence = "provide_account_type", 0.8
    elif any(word in text_lower for word in ["savings", "saving"]):
        intent_name, confidence = "provide_account_type", 0.8
    else:
        intent_name, confidence = "out_of_scope", 0.5

    return {
        "intent": {"name": intent_name, "confidence": confidence},
        "entities": entities,
        "sentiment": {"label": "neutral", "score": 0.5}
    }


class VoiceFlowEngine:
    """Voice conversation flow engine for banking operations"""
    
    WORKFLOWS = {
        "check_balance": {
            "name": "Balance Inquiry",
            "steps": [
                {"id": "ask_account", "type": "slot_fill", "slot": "account_type", "prompt": "Which account would you like to check? Checking, savings, or credit?"},
                {"id": "fetch_balance", "type": "action", "action": "get_balance"},
                {"id": "respond", "type": "response"}
            ]
        },
        "transfer_money": {
            "name": "Money Transfer",
            "steps": [
                {"id": "ask_amount", "type": "slot_fill", "slot": "amount", "prompt": "How much would you like to transfer?"},
                {"id": "ask_from", "type": "slot_fill", "slot": "from_account", "prompt": "Which account would you like to transfer from? Checking or savings?"},
                {"id": "ask_to", "type": "slot_fill", "slot": "to_account", "prompt": "Which account would you like to transfer to?"},
                {"id": "confirm", "type": "confirm", "prompt": "You want to transfer ${amount} from {from_account} to {to_account}. Is that correct?"},
                {"id": "execute", "type": "action", "action": "execute_transfer"},
                {"id": "respond", "type": "response"}
            ]
        },
        "account_statement": {
            "name": "Account Statement",
            "steps": [
                {"id": "ask_account", "type": "slot_fill", "slot": "account_type", "prompt": "Which account statement would you like? Checking, savings, or credit?"},
                {"id": "respond", "type": "response"}
            ]
        }
    }
    
    BALANCES = {
        "checking": 1234.56,
        "savings": 5678.90,
        "credit": -450.00,
        "money market": 10000.00,
        "investment": 25000.00
    }
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def get_session(self, call_sid: str) -> Dict[str, Any]:
        if call_sid not in self.sessions:
            self.sessions[call_sid] = {
                "call_sid": call_sid,
                "state": "greeting",
                "workflow": None,
                "current_step": 0,
                "slots": {},
                "turn_count": 0,
                "awaiting_confirmation": False
            }
        return self.sessions[call_sid]
    
    def process_input(self, call_sid: str, user_text: str) -> Dict[str, Any]:
        """Process user voice input and return response"""
        session = self.get_session(call_sid)
        session["turn_count"] += 1
        
        nlu_result = fallback_intent(user_text)
        intent = nlu_result["intent"]["name"]
        entities = nlu_result["entities"]
        
        for entity in entities:
            if entity["entity_type"] == "account_type":
                session["slots"]["account_type"] = entity["value"]
            elif entity["entity_type"] == "amount":
                session["slots"]["amount"] = entity["value"]
            elif entity["entity_type"] == "confirmation":
                session["last_confirmation"] = entity["value"]
        
        if intent == "goodbye":
            return {
                "response": "Thank you for calling B2T Voice Banking. Have a great day! Goodbye!",
                "end_call": True,
                "intent": intent
            }
        
        if intent == "transfer_agent":
            return {
                "response": "I'll connect you with a customer service representative. Please hold.",
                "end_call": False,
                "transfer_to_agent": True,
                "intent": intent
            }
        
        if session["state"] == "greeting" or session["workflow"] is None:
            return self._handle_new_intent(session, intent, entities, user_text)
        
        return self._continue_workflow(session, intent, entities, user_text)
    
    def _handle_new_intent(self, session: Dict, intent: str, entities: list, user_text: str) -> Dict[str, Any]:
        """Handle a new intent and start appropriate workflow"""
        
        if intent == "greet":
            return {
                "response": "Hello! Welcome to B2T Voice Banking. I can help you check your balance, transfer money, or get your account statement. What would you like to do?",
                "end_call": False,
                "intent": intent
            }
        
        if intent == "help":
            return {
                "response": "I can help you with: checking your account balance, transferring money between accounts, or getting your account statement. What would you like to do?",
                "end_call": False,
                "intent": intent
            }
        
        if intent == "check_balance":
            session["workflow"] = "check_balance"
            session["current_step"] = 0
            session["state"] = "in_workflow"
            
            if session["slots"].get("account_type"):
                return self._get_balance_response(session)
            
            return {
                "response": "I can check your balance. Which account would you like to check? Checking, savings, or credit?",
                "end_call": False,
                "intent": intent
            }
        
        if intent == "transfer_money":
            session["workflow"] = "transfer_money"
            session["current_step"] = 0
            session["state"] = "in_workflow"
            
            if session["slots"].get("amount"):
                session["current_step"] = 1
                return {
                    "response": f"I'll help you transfer ${session['slots']['amount']:.2f}. Which account would you like to transfer from? Checking or savings?",
                    "end_call": False,
                    "intent": intent
                }
            
            return {
                "response": "I can help you transfer money. How much would you like to transfer?",
                "end_call": False,
                "intent": intent
            }
        
        if intent == "account_statement":
            session["workflow"] = "account_statement"
            session["state"] = "in_workflow"
            
            if session["slots"].get("account_type"):
                account = session["slots"]["account_type"]
                return {
                    "response": f"I'll send your {account} account statement to your registered email address. You should receive it within a few minutes. Is there anything else I can help you with?",
                    "end_call": False,
                    "intent": intent
                }
            
            return {
                "response": "Which account statement would you like? Checking, savings, or credit?",
                "end_call": False,
                "intent": intent
            }
        
        if intent == "card_services":
            return {
                "response": "For card services including lost or stolen cards, please press 1 to be connected to our card services team, or I can help you with account inquiries.",
                "end_call": False,
                "intent": intent
            }
        
        return {
            "response": "I can help you check your balance, transfer money, or get your account statement. What would you like to do?",
            "end_call": False,
            "intent": intent
        }
    
    def _continue_workflow(self, session: Dict, intent: str, entities: list, user_text: str) -> Dict[str, Any]:
        """Continue an in-progress workflow"""
        workflow = session["workflow"]
        
        if workflow == "check_balance":
            return self._process_check_balance(session, intent, entities, user_text)
        elif workflow == "transfer_money":
            return self._process_transfer(session, intent, entities, user_text)
        elif workflow == "account_statement":
            return self._process_statement(session, intent, entities, user_text)
        
        session["workflow"] = None
        session["state"] = "greeting"
        return self._handle_new_intent(session, intent, entities, user_text)
    
    def _process_check_balance(self, session: Dict, intent: str, entities: list, user_text: str) -> Dict[str, Any]:
        """Process check balance workflow"""
        if not session["slots"].get("account_type"):
            account_entity = next((e for e in entities if e["entity_type"] == "account_type"), None)
            if account_entity:
                session["slots"]["account_type"] = account_entity["value"]
            elif intent == "provide_account_type":
                text_lower = user_text.lower()
                if "checking" in text_lower:
                    session["slots"]["account_type"] = "checking"
                elif "saving" in text_lower:
                    session["slots"]["account_type"] = "savings"
                elif "credit" in text_lower:
                    session["slots"]["account_type"] = "credit"
        
        if session["slots"].get("account_type"):
            return self._get_balance_response(session)
        
        return {
            "response": "I didn't catch that. Which account would you like to check? Checking, savings, or credit?",
            "end_call": False,
            "intent": intent
        }
    
    def _get_balance_response(self, session: Dict) -> Dict[str, Any]:
        """Generate balance response"""
        account = session["slots"]["account_type"]
        balance = self.BALANCES.get(account, 0)
        
        session["workflow"] = None
        session["state"] = "greeting"
        session["slots"] = {}
        
        if balance < 0:
            return {
                "response": f"Your {account} account has an outstanding balance of ${abs(balance):.2f}. Is there anything else I can help you with?",
                "end_call": False,
                "intent": "check_balance"
            }
        
        return {
            "response": f"Your {account} account balance is ${balance:.2f}. Is there anything else I can help you with?",
            "end_call": False,
            "intent": "check_balance"
        }
    
    def _process_transfer(self, session: Dict, intent: str, entities: list, user_text: str) -> Dict[str, Any]:
        """Process money transfer workflow"""
        
        if session.get("awaiting_confirmation"):
            if intent == "confirm" or session.get("last_confirmation") == True:
                session["awaiting_confirmation"] = False
                amount = session["slots"]["amount"]
                from_acc = session["slots"]["from_account"]
                to_acc = session["slots"]["to_account"]
                
                session["workflow"] = None
                session["state"] = "greeting"
                session["slots"] = {}
                
                return {
                    "response": f"Transfer complete! I've moved ${amount:.2f} from your {from_acc} account to your {to_acc} account. Your confirmation number is T-{uuid.uuid4().hex[:8].upper()}. Is there anything else I can help you with?",
                    "end_call": False,
                    "intent": "transfer_complete"
                }
            elif intent == "deny" or session.get("last_confirmation") == False:
                session["awaiting_confirmation"] = False
                session["workflow"] = None
                session["state"] = "greeting"
                session["slots"] = {}
                
                return {
                    "response": "Transfer cancelled. Is there anything else I can help you with?",
                    "end_call": False,
                    "intent": "transfer_cancelled"
                }
        
        if not session["slots"].get("amount"):
            amount_entity = next((e for e in entities if e["entity_type"] == "amount"), None)
            if amount_entity:
                session["slots"]["amount"] = amount_entity["value"]
            else:
                return {
                    "response": "How much would you like to transfer? Please say an amount.",
                    "end_call": False,
                    "intent": intent
                }
        
        if not session["slots"].get("from_account"):
            account_entity = next((e for e in entities if e["entity_type"] == "account_type"), None)
            if account_entity:
                session["slots"]["from_account"] = account_entity["value"]
                return {
                    "response": f"Transfer ${session['slots']['amount']:.2f} from {account_entity['value']}. Which account would you like to transfer to?",
                    "end_call": False,
                    "intent": intent
                }
            return {
                "response": f"I'll transfer ${session['slots']['amount']:.2f}. Which account would you like to transfer from? Checking or savings?",
                "end_call": False,
                "intent": intent
            }
        
        if not session["slots"].get("to_account"):
            account_entity = next((e for e in entities if e["entity_type"] == "account_type"), None)
            if account_entity and account_entity["value"] != session["slots"]["from_account"]:
                session["slots"]["to_account"] = account_entity["value"]
            else:
                text_lower = user_text.lower()
                if "checking" in text_lower and session["slots"]["from_account"] != "checking":
                    session["slots"]["to_account"] = "checking"
                elif "saving" in text_lower and session["slots"]["from_account"] != "savings":
                    session["slots"]["to_account"] = "savings"
                elif "credit" in text_lower:
                    session["slots"]["to_account"] = "credit"
                else:
                    return {
                        "response": "Which account would you like to transfer to? Please choose a different account than the source.",
                        "end_call": False,
                        "intent": intent
                    }
        
        amount = session["slots"]["amount"]
        from_acc = session["slots"]["from_account"]
        to_acc = session["slots"]["to_account"]
        session["awaiting_confirmation"] = True
        
        return {
            "response": f"Let me confirm: Transfer ${amount:.2f} from your {from_acc} account to your {to_acc} account. Is that correct?",
            "end_call": False,
            "intent": "confirm_transfer"
        }
    
    def _process_statement(self, session: Dict, intent: str, entities: list, user_text: str) -> Dict[str, Any]:
        """Process account statement request"""
        if not session["slots"].get("account_type"):
            account_entity = next((e for e in entities if e["entity_type"] == "account_type"), None)
            if account_entity:
                session["slots"]["account_type"] = account_entity["value"]
            else:
                text_lower = user_text.lower()
                if "checking" in text_lower:
                    session["slots"]["account_type"] = "checking"
                elif "saving" in text_lower:
                    session["slots"]["account_type"] = "savings"
                elif "credit" in text_lower:
                    session["slots"]["account_type"] = "credit"
        
        if session["slots"].get("account_type"):
            account = session["slots"]["account_type"]
            session["workflow"] = None
            session["state"] = "greeting"
            session["slots"] = {}
            
            return {
                "response": f"I'll send your {account} account statement to your registered email address. You should receive it within a few minutes. Is there anything else I can help you with?",
                "end_call": False,
                "intent": "statement_sent"
            }
        
        return {
            "response": "Which account statement would you like? Checking, savings, or credit?",
            "end_call": False,
            "intent": intent
        }
    
    def end_session(self, call_sid: str):
        """Clean up session when call ends"""
        self.sessions.pop(call_sid, None)


voice_flow_engine = VoiceFlowEngine()


async def get_flow_definition(db: AsyncSession, flow_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not flow_id:
        return None
    result = await db.execute(
        text("SELECT flow_definition FROM dialogue_flows WHERE flow_id = :flow_id"),
        {"flow_id": flow_id}
    )
    row = result.fetchone()
    return row[0] if row else None


def execute_node(node: Dict[str, Any], slots: Dict[str, Any], intent: str, entities: list) -> Dict[str, Any]:
    node_type = node.get("type")

    if node_type == "greeting":
        return {
            "response_text": node.get("template", "Hello!"),
            "next_node": node.get("next", "intent_router"),
            "next_action": {"action_type": "wait_for_input"},
            "context_updates": {}
        }
    elif node_type in ["intent_classifier", "intent_router"]:
        intent_mapping = node.get("intent_mapping", {})
        next_node_id = intent_mapping.get(intent, node.get("default_next", "fallback"))
        return {
            "response_text": "",
            "next_node": next_node_id,
            "next_action": {"action_type": "continue"},
            "context_updates": {}
        }
    elif node_type == "response":
        template = node.get("template", "")
        for key, value in slots.items():
            template = template.replace(f"{{{key}}}", str(value))
        next_node = node.get("next")
        action_type = "continue" if next_node else "end_conversation"
        return {
            "response_text": template,
            "next_node": next_node,
            "next_action": {"action_type": action_type},
            "context_updates": {}
        }
    elif node_type == "slot_filler":
        slot_name = node.get("slot_name")
        slot_value = next((e.get("value") for e in entities if e.get("entity_type") == slot_name), None)
        if slot_value:
            slots[slot_name] = slot_value
            acknowledgment = node.get("acknowledgment_template", "Got it!")
            for key, value in slots.items():
                acknowledgment = acknowledgment.replace(f"{{{key}}}", str(value))
            return {
                "response_text": acknowledgment,
                "next_node": node.get("next_on_filled", "intent_router"),
                "next_action": {"action_type": "continue"},
                "context_updates": slots
            }
        else:
            prompt = node.get("prompt_template", f"Please provide {slot_name}")
            return {
                "response_text": prompt,
                "next_node": node.get("id"),
                "next_action": {"action_type": "wait_for_input"},
                "context_updates": {}
            }
    else:
        return {
            "response_text": "I'm sorry, I didn't understand that. I can help you check your balance or transfer money.",
            "next_node": "intent_router",
            "next_action": {"action_type": "wait_for_input"},
            "context_updates": {}
        }


async def execute_flow(db: AsyncSession, session_id: str, session_context: Dict[str, Any], intent: str, entities: list) -> Dict[str, Any]:
    flow_id = session_context.get("flow_id")
    current_node = session_context.get("current_node", "start")
    slots = session_context.get("slots", {})

    flow_def = await get_flow_definition(db, flow_id)
    if not flow_def:
        return {
            "response_text": "I'm sorry, I didn't understand that. I can help you check your balance or transfer money.",
            "next_node": "intent_router",
            "next_action": {"action_type": "wait_for_input"},
            "context_updates": {}
        }

    nodes = flow_def.get("nodes", [])
    global_intents = flow_def.get("global_intents", {})
    
    if intent in global_intents:
        target_node_id = global_intents[intent]
        node = next((n for n in nodes if n.get("id") == target_node_id), None)
        if node:
            return execute_node(node, slots, intent, entities)

    if current_node in ["intent_router", "start"]:
        router = next((n for n in nodes if n.get("type") in ["intent_classifier", "intent_router"]), None)
        if router:
            intent_mapping = router.get("intent_mapping", {})
            next_node_id = intent_mapping.get(intent, router.get("default_next", "fallback"))
            node = next((n for n in nodes if n.get("id") == next_node_id), None)
            if node:
                return execute_node(node, slots, intent, entities)
    else:
        node = next((n for n in nodes if n.get("id") == current_node), None)
        if node:
            return execute_node(node, slots, intent, entities)

    return {
        "response_text": "I'm sorry, I didn't understand that. I can help you check your balance or transfer money.",
        "next_node": "intent_router",
        "next_action": {"action_type": "wait_for_input"},
        "context_updates": {}
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting OCP Platform...")
    
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    try:
        await redis_client.connect()
        await redis_client.ping()
        logger.info("Redis connection successful (or using in-memory fallback)")
    except Exception as e:
        logger.warning(f"Redis connection issue: {e}")

    logger.info("OCP Platform started successfully!")
    yield
    
    logger.info("Shutting down OCP Platform...")
    await engine.dispose()
    await redis_client.close()


app = FastAPI(
    title="OCP Platform",
    description="Conversational AI Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def serve_portal():
    return FileResponse("frontend/portal/index.html")


@app.get("/chat")
async def serve_chat():
    return FileResponse("frontend/chat-widget/index.html")


app.mount("/portal", StaticFiles(directory="frontend/portal"), name="portal")


@app.get("/api/stats")
async def get_stats():
    return {
        "conversations_today": 1234,
        "success_rate": 98.5,
        "avg_response_time": 1.2,
        "active_users": 542
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0", "environment": settings.ENVIRONMENT}


@app.post("/voice/incoming")
async def voice_incoming(
    CallSid: str = Form(None),
    From: str = Form(None),
    To: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle incoming Twilio voice call - Entry point for voice conversations"""
    twiml = VoiceResponse()
    
    session = voice_flow_engine.get_session(CallSid)
    session["from"] = From
    session["to"] = To
    
    logger.info(f"Incoming voice call: {CallSid} from {From}")
    
    gather = Gather(
        input='speech',
        action='/voice/process',
        method='POST',
        timeout=5,
        speech_timeout='auto',
        language='en-US'
    )
    gather.say(
        "Hello! Welcome to B2T Voice Banking. I can help you check your balance, transfer money, or get your account statement. What would you like to do?",
        voice='Polly.Joanna'
    )
    twiml.append(gather)
    
    twiml.say("I didn't catch that. Please call back when you're ready. Goodbye!", voice='Polly.Joanna')
    twiml.hangup()
    
    return Response(content=str(twiml), media_type="application/xml")


@app.post("/voice/process")
async def voice_process(
    CallSid: str = Form(None),
    SpeechResult: str = Form(None),
    Confidence: float = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Process speech input through the voice flow engine"""
    twiml = VoiceResponse()
    
    user_text = SpeechResult or ""
    logger.info(f"Voice input from {CallSid}: '{user_text}' (confidence: {Confidence})")
    
    result = voice_flow_engine.process_input(CallSid, user_text)
    bot_response = result["response"]
    
    logger.info(f"Voice response to {CallSid}: '{bot_response[:50]}...' (intent: {result.get('intent', 'unknown')})")
    
    if result.get("end_call"):
        twiml.say(bot_response, voice='Polly.Joanna')
        twiml.hangup()
        voice_flow_engine.end_session(CallSid)
        return Response(content=str(twiml), media_type="application/xml")
    
    if result.get("transfer_to_agent"):
        twiml.say(bot_response, voice='Polly.Joanna')
        twiml.dial("+1234567890")
        return Response(content=str(twiml), media_type="application/xml")
    
    gather = Gather(
        input='speech',
        action='/voice/process',
        method='POST',
        timeout=6,
        speech_timeout='auto',
        language='en-US'
    )
    gather.say(bot_response, voice='Polly.Joanna')
    twiml.append(gather)
    
    twiml.say("I didn't hear anything. Is there anything else I can help you with?", voice='Polly.Joanna')
    
    no_input_gather = Gather(
        input='speech',
        action='/voice/process',
        method='POST',
        timeout=5,
        speech_timeout='auto',
        language='en-US'
    )
    no_input_gather.say("I'm still here if you need help.", voice='Polly.Joanna')
    twiml.append(no_input_gather)
    
    twiml.say("Thank you for calling B2T Voice Banking. Goodbye!", voice='Polly.Joanna')
    twiml.hangup()
    
    return Response(content=str(twiml), media_type="application/xml")


@app.post("/voice/status")
async def voice_status(
    CallSid: str = Form(None),
    CallStatus: str = Form(None)
):
    """Handle call status updates from Twilio"""
    logger.info(f"Call status update: {CallSid} -> {CallStatus}")
    if CallStatus in ["completed", "failed", "busy", "no-answer", "canceled"]:
        voice_flow_engine.end_session(CallSid)
    return {"status": "ok"}


@app.post("/v1/conversations/start", status_code=201)
async def start_conversation(request: SessionStartRequest, db: AsyncSession = Depends(get_db)):
    session_id = uuid.uuid4()
    started_at = datetime.utcnow()

    result = await db.execute(
        text("SELECT flow_id FROM dialogue_flows WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 1")
    )
    row = result.fetchone()
    flow_id = str(row[0]) if row else None

    await db.execute(
        text("""
        INSERT INTO sessions (session_id, channel_type, caller_id, started_at, current_state, context, assigned_flow_id)
        VALUES (:session_id, :channel_type, :caller_id, :started_at, 'started', CAST(:context AS jsonb), CAST(:flow_id AS uuid))
        """),
        {
            "session_id": session_id,
            "channel_type": request.channel_type.value,
            "caller_id": request.caller_id,
            "started_at": started_at,
            "context": json.dumps(request.initial_context or {}),
            "flow_id": flow_id
        }
    )
    await db.commit()

    session_context = {
        "session_id": str(session_id),
        "channel_type": request.channel_type.value,
        "current_node": "start",
        "current_state": "started",
        "slots": request.initial_context or {},
        "turn_count": 0,
        "started_at": started_at.isoformat(),
        "flow_id": flow_id
    }
    await redis_client.set_session(str(session_id), session_context)

    initial_message = "Hello! I'm your banking assistant. How can I help you today?"
    if flow_id:
        flow_def = await get_flow_definition(db, flow_id)
        if flow_def:
            nodes = flow_def.get("nodes", [])
            start_node = next((n for n in nodes if n.get("id") == "start"), None)
            if start_node:
                initial_message = start_node.get("template", initial_message)

    logger.info(f"Created session {session_id}")

    return {
        "session_id": str(session_id),
        "channel_type": request.channel_type.value,
        "started_at": started_at.isoformat(),
        "initial_message": initial_message
    }


@app.post("/v1/conversations/{session_id}/process")
async def process_turn(session_id: str, request: UserInputRequest, db: AsyncSession = Depends(get_db)):
    start_time = time.time()

    session_context = await redis_client.get_session(session_id)
    if not session_context:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    if request.input_type == InputType.AUDIO:
        raise HTTPException(status_code=501, detail="Voice input not yet implemented")

    user_text = request.text or ""
    nlu_result = fallback_intent(user_text)

    logger.info(f"Session {session_id}: Input: {user_text}, Intent: {nlu_result['intent']['name']}")

    flow_result = await execute_flow(
        db, session_id, session_context,
        nlu_result["intent"]["name"],
        nlu_result["entities"]
    )

    turn_number = session_context.get("turn_count", 0) + 1
    
    await redis_client.set_session(session_id, {
        **session_context,
        "current_node": flow_result["next_node"],
        "slots": {**session_context.get("slots", {}), **flow_result.get("context_updates", {})},
        "turn_count": turn_number
    })

    await db.execute(
        text("""
        INSERT INTO conversation_turns (session_id, turn_number, speaker, user_input_text, detected_intent, intent_confidence, extracted_entities, bot_response_text, bot_action, timestamp)
        VALUES (CAST(:session_id AS uuid), :turn_number, 'user', :user_input_text, :detected_intent, :intent_confidence, CAST(:extracted_entities AS jsonb), :bot_response_text, :bot_action, NOW())
        """),
        {
            "session_id": session_id,
            "turn_number": turn_number,
            "user_input_text": user_text,
            "detected_intent": nlu_result["intent"]["name"],
            "intent_confidence": nlu_result["intent"]["confidence"],
            "extracted_entities": json.dumps(nlu_result["entities"]),
            "bot_response_text": flow_result["response_text"],
            "bot_action": flow_result["next_action"]["action_type"]
        }
    )
    await db.commit()

    processing_time_ms = int((time.time() - start_time) * 1000)

    return {
        "session_id": session_id,
        "turn_number": turn_number,
        "nlu": nlu_result,
        "response": {
            "type": "text",
            "text": flow_result["response_text"],
            "audio_url": None
        },
        "next_action": flow_result["next_action"],
        "updated_context": flow_result.get("context_updates", {}),
        "processing_time_ms": processing_time_ms,
        "confidence_score": nlu_result["intent"]["confidence"]
    }


@app.post("/v1/conversations/{session_id}/end")
async def end_conversation(session_id: str, request: SessionEndRequest, db: AsyncSession = Depends(get_db)):
    session_context = await redis_client.get_session(session_id)
    if not session_context:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.execute(
        text("UPDATE sessions SET ended_at = NOW(), current_state = :reason WHERE session_id = CAST(:session_id AS uuid)"),
        {"session_id": session_id, "reason": request.reason}
    )
    await db.commit()

    result = await db.execute(
        text("SELECT duration_seconds FROM sessions WHERE session_id = CAST(:session_id AS uuid)"),
        {"session_id": session_id}
    )
    duration = result.scalar() or 0

    await redis_client.delete_session(session_id)

    return {
        "session_id": session_id,
        "duration_seconds": duration,
        "turn_count": session_context.get("turn_count", 0),
        "summary": {"reason": request.reason}
    }


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)


ws_manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    session_id = None
    
    try:
        await websocket.accept()
        logger.info("New WebSocket connection")

        async with AsyncSessionLocal() as db:
            session_id_uuid = uuid.uuid4()
            session_id = str(session_id_uuid)
            started_at = datetime.utcnow()

            result = await db.execute(
                text("SELECT flow_id FROM dialogue_flows WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 1")
            )
            row = result.fetchone()
            flow_id = str(row[0]) if row else None

            await db.execute(
                text("""
                INSERT INTO sessions (session_id, channel_type, started_at, current_state, context, assigned_flow_id)
                VALUES (:session_id, 'chat', :started_at, 'started', '{}', CAST(:flow_id AS uuid))
                """),
                {"session_id": session_id_uuid, "started_at": started_at, "flow_id": flow_id}
            )
            await db.commit()

            session_context = {
                "session_id": session_id,
                "channel_type": "chat",
                "current_node": "start",
                "slots": {},
                "turn_count": 0,
                "started_at": started_at.isoformat(),
                "flow_id": flow_id
            }
            await redis_client.set_session(session_id, session_context)

            initial_message = "Hello! I'm your banking assistant. How can I help you today?"
            if flow_id:
                flow_def = await get_flow_definition(db, flow_id)
                if flow_def:
                    nodes = flow_def.get("nodes", [])
                    start_node = next((n for n in nodes if n.get("id") == "start"), None)
                    if start_node:
                        initial_message = start_node.get("template", initial_message)

            ws_manager.active_connections[session_id] = websocket

            await websocket.send_json({
                "type": "session_created",
                "session_id": session_id,
                "message": initial_message
            })

            while True:
                data = await websocket.receive_json()
                message_type = data.get("type")

                if message_type == "message":
                    user_text = data.get("text", "").strip()
                    if not user_text:
                        await websocket.send_json({"type": "error", "message": "Empty message"})
                        continue

                    await websocket.send_json({"type": "typing", "is_typing": True})

                    session_context = await redis_client.get_session(session_id)
                    nlu_result = fallback_intent(user_text)

                    flow_result = await execute_flow(
                        db, session_id, session_context,
                        nlu_result["intent"]["name"],
                        nlu_result["entities"]
                    )

                    turn_number = session_context.get("turn_count", 0) + 1
                    await redis_client.set_session(session_id, {
                        **session_context,
                        "current_node": flow_result["next_node"],
                        "slots": {**session_context.get("slots", {}), **flow_result.get("context_updates", {})},
                        "turn_count": turn_number
                    })

                    await websocket.send_json({
                        "type": "message",
                        "speaker": "bot",
                        "text": flow_result["response_text"],
                        "intent": nlu_result["intent"]["name"],
                        "confidence": nlu_result["intent"]["confidence"],
                        "turn_number": turn_number
                    })

                    if flow_result["next_action"]["action_type"] == "end_conversation":
                        await websocket.send_json({
                            "type": "conversation_ended",
                            "message": "Thank you for using OCP Platform!"
                        })
                        break

                elif message_type == "end":
                    await websocket.send_json({"type": "session_ended", "message": "Goodbye!"})
                    break

                elif message_type == "ping":
                    await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if session_id:
            ws_manager.disconnect(session_id)
            await redis_client.delete_session(session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
