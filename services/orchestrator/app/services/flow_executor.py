"""
Dialogue flow execution engine
Executes dialogue flows based on state machine logic
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any, List, Optional
import logging
import re

logger = logging.getLogger(__name__)


class FlowExecutor:
    """Executes dialogue flow state machine"""

    def __init__(self, db: AsyncSession, redis_client):
        self.db = db
        self.redis = redis_client

    async def get_initial_message(self, session_id: str) -> str:
        """
        Get initial greeting message for a session

        Args:
            session_id: Session UUID string

        Returns:
            Initial greeting text
        """
        # Get session context
        context = await self.redis.get_session(session_id)
        if not context:
            return "Hello! How can I help you today?"

        flow_id = context.get("flow_id")
        if not flow_id:
            return "Hello! How can I help you today?"

        # Get flow definition
        flow_def = await self._get_flow_definition(flow_id)
        if not flow_def:
            return "Hello! How can I help you today?"

        # Find start node
        nodes = flow_def.get("nodes", [])
        start_node = next((n for n in nodes if n.get("id") == "start"), None)

        if start_node:
            return start_node.get("template", "Hello! How can I help you today?")

        return "Hello! How can I help you today?"

    async def execute_flow(
        self,
        session_id: str,
        session_context: Dict[str, Any],
        intent: str,
        entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute dialogue flow logic

        Args:
            session_id: Session UUID string
            session_context: Current session context from Redis
            intent: Detected intent from NLU
            entities: Extracted entities from NLU

        Returns:
            Dictionary with:
            - response_text: Text to send to user
            - next_node: Next node in flow
            - next_action: Action to take
            - context_updates: Updates to session slots
        """
        flow_id = session_context.get("flow_id")
        current_node = session_context.get("current_node", "start")
        slots = session_context.get("slots", {})

        # Get flow definition
        flow_def = await self._get_flow_definition(flow_id)
        if not flow_def:
            return self._fallback_response(intent)

        # Check global intents (cancel, help)
        global_intents = flow_def.get("global_intents", {})
        if intent in global_intents:
            target_node_id = global_intents[intent]
            node = self._find_node(flow_def, target_node_id)
            if node:
                return self._execute_node(node, slots, intent, entities)

        # Get current node or route from intent
        if current_node == "intent_router" or current_node == "start":
            # Route based on intent
            node = self._route_by_intent(flow_def, intent)
        else:
            # Continue from current node
            node = self._find_node(flow_def, current_node)

        if not node:
            return self._fallback_response(intent)

        # Execute node logic
        return self._execute_node(node, slots, intent, entities)

    def _execute_node(
        self,
        node: Dict[str, Any],
        slots: Dict[str, Any],
        intent: str,
        entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute logic for a specific node

        Args:
            node: Node definition from flow
            slots: Current slot values
            intent: Detected intent
            entities: Extracted entities

        Returns:
            Execution result with response and next steps
        """
        node_type = node.get("type")

        if node_type == "greeting":
            return {
                "response_text": node.get("template", "Hello!"),
                "next_node": node.get("next", "intent_router"),
                "next_action": {
                    "action_type": "wait_for_input"
                },
                "context_updates": {}
            }

        elif node_type == "intent_classifier" or node_type == "intent_router":
            # Route to next node based on intent
            intent_mapping = node.get("intent_mapping", {})
            next_node_id = intent_mapping.get(intent, node.get("default_next", "fallback"))

            return {
                "response_text": "",  # No response, just routing
                "next_node": next_node_id,
                "next_action": {
                    "action_type": "continue"
                },
                "context_updates": {}
            }

        elif node_type == "response":
            # Simple response node
            template = node.get("template", "")
            response_text = self._render_template(template, slots)

            next_node = node.get("next")
            if next_node:
                action_type = "continue"
            else:
                action_type = "end_conversation"

            return {
                "response_text": response_text,
                "next_node": next_node,
                "next_action": {
                    "action_type": action_type
                },
                "context_updates": {}
            }

        elif node_type == "slot_filler":
            # Slot filling node
            slot_name = node.get("slot_name")
            slot_value = self._extract_slot_value(entities, slot_name)

            if slot_value:
                # Slot filled
                slots[slot_name] = slot_value
                acknowledgment = node.get("acknowledgment_template", "Got it!")
                response_text = self._render_template(acknowledgment, slots)

                return {
                    "response_text": response_text,
                    "next_node": node.get("next_on_filled", "intent_router"),
                    "next_action": {
                        "action_type": "continue"
                    },
                    "context_updates": slots
                }
            else:
                # Slot not filled, ask for it
                prompt = node.get("prompt_template", f"Please provide {slot_name}")
                response_text = self._render_template(prompt, slots)

                return {
                    "response_text": response_text,
                    "next_node": node.get("id"),  # Stay on same node
                    "next_action": {
                        "action_type": "wait_for_input"
                    },
                    "context_updates": {}
                }

        elif node_type == "api_caller":
            # API call node (Phase 2)
            return {
                "response_text": "Processing your request...",
                "next_node": node.get("next"),
                "next_action": {
                    "action_type": "execute_api_call"
                },
                "api_call_needed": True,
                "context_updates": {}
            }

        else:
            logger.warning(f"Unknown node type: {node_type}")
            return self._fallback_response(intent)

    def _route_by_intent(self, flow_def: Dict[str, Any], intent: str) -> Optional[Dict[str, Any]]:
        """
        Find the node to route to based on intent

        Args:
            flow_def: Flow definition
            intent: Detected intent

        Returns:
            Node definition or None
        """
        nodes = flow_def.get("nodes", [])

        # Find intent_router node
        router = next((n for n in nodes if n.get("type") == "intent_classifier" or n.get("type") == "intent_router"), None)

        if router:
            intent_mapping = router.get("intent_mapping", {})
            next_node_id = intent_mapping.get(intent, router.get("default_next", "fallback"))
            return self._find_node(flow_def, next_node_id)

        # No router found, look for node with matching intent
        for node in nodes:
            if node.get("intent") == intent:
                return node

        return None

    def _find_node(self, flow_def: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
        """Find a node by ID in flow definition"""
        nodes = flow_def.get("nodes", [])
        return next((n for n in nodes if n.get("id") == node_id), None)

    def _render_template(self, template: str, slots: Dict[str, Any]) -> str:
        """
        Render a template string with slot values

        Args:
            template: Template string with {slot_name} placeholders
            slots: Dictionary of slot values

        Returns:
            Rendered string
        """
        result = template
        for key, value in slots.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))

        return result

    def _extract_slot_value(self, entities: List[Dict[str, Any]], slot_name: str) -> Optional[str]:
        """
        Extract slot value from entities

        Args:
            entities: List of extracted entities
            slot_name: Name of slot to extract

        Returns:
            Slot value or None
        """
        for entity in entities:
            if entity.get("entity_type") == slot_name:
                return entity.get("value")

        return None

    def _fallback_response(self, intent: str) -> Dict[str, Any]:
        """
        Generate fallback response when flow execution fails

        Args:
            intent: Detected intent

        Returns:
            Fallback execution result
        """
        logger.warning(f"Fallback response for intent: {intent}")

        return {
            "response_text": "I'm sorry, I didn't understand that. I can help you check your balance or transfer money. What would you like to do?",
            "next_node": "intent_router",
            "next_action": {
                "action_type": "wait_for_input"
            },
            "context_updates": {}
        }

    async def _get_flow_definition(self, flow_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Get flow definition from database

        Args:
            flow_id: Flow UUID string

        Returns:
            Flow definition JSON or None
        """
        if not flow_id:
            return None

        result = await self.db.execute(
            text("SELECT flow_definition FROM dialogue_flows WHERE flow_id = :flow_id"),
            {"flow_id": flow_id}
        )
        row = result.fetchone()

        if row:
            return row[0]  # JSONB column

        return None
