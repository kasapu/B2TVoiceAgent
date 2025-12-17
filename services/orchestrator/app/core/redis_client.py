"""
Redis client for session state management
"""

import redis.asyncio as redis
import json
from typing import Optional, Dict, Any
import logging

from .config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper for session management"""

    def __init__(self):
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Initialize Redis connection"""
        if not self.client:
            self.client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )

    async def ping(self):
        """Test Redis connection"""
        if not self.client:
            await self.connect()
        return await self.client.ping()

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session context from Redis

        Args:
            session_id: UUID of the session

        Returns:
            Session context dict or None if not found
        """
        if not self.client:
            await self.connect()

        key = f"session:{session_id}"
        data = await self.client.get(key)

        if data:
            return json.loads(data)
        return None

    async def set_session(
        self,
        session_id: str,
        context: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store session context in Redis

        Args:
            session_id: UUID of the session
            context: Session context dictionary
            ttl: Time to live in seconds (default: from settings)

        Returns:
            True if successful
        """
        if not self.client:
            await self.connect()

        key = f"session:{session_id}"
        ttl = ttl or settings.SESSION_TIMEOUT_SECONDS

        data = json.dumps(context)
        await self.client.setex(key, ttl, data)
        return True

    async def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update specific fields in session context

        Args:
            session_id: UUID of the session
            updates: Dictionary of fields to update

        Returns:
            True if successful
        """
        context = await self.get_session(session_id)
        if not context:
            logger.warning(f"Session {session_id} not found in Redis")
            return False

        # Merge updates
        context.update(updates)

        # Save back to Redis
        return await self.set_session(session_id, context)

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session from Redis

        Args:
            session_id: UUID of the session

        Returns:
            True if deleted
        """
        if not self.client:
            await self.connect()

        key = f"session:{session_id}"
        result = await self.client.delete(key)
        return result > 0

    async def get_ttl(self, session_id: str) -> int:
        """
        Get remaining TTL for session

        Args:
            session_id: UUID of the session

        Returns:
            TTL in seconds, -1 if no expiry, -2 if doesn't exist
        """
        if not self.client:
            await self.connect()

        key = f"session:{session_id}"
        return await self.client.ttl(key)


# Global Redis client instance
redis_client = RedisClient()
