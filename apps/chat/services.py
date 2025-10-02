import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import redis

from django.conf import settings


class RedisMessageService:
    """Service for managing messages in Redis"""

    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.message_ttl = 86400 * 30  # 30 days

    def store_message(
        self, conversation_id: str, sender_id: str, receiver_id: str, content: str
    ) -> str:
        """Store message in Redis and return message ID"""
        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        message_data = {
            "id": message_id,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "content": content,
            "timestamp": timestamp,
        }

        # Store message with TTL
        message_key = f"message:{message_id}"
        self.redis_client.setex(message_key, self.message_ttl, json.dumps(message_data))

        # Add to conversation message list
        conversation_key = f"conversation:{conversation_id}:messages"
        # Convert timestamp to float for Redis sorted set
        timestamp_float = datetime.utcnow().timestamp()
        self.redis_client.zadd(conversation_key, {message_id: timestamp_float})
        self.redis_client.expire(conversation_key, self.message_ttl)

        return message_id

    def get_message(self, message_id: str) -> Optional[Dict]:
        """Get message by ID"""
        message_key = f"message:{message_id}"
        message_data = self.redis_client.get(message_key)

        if message_data:
            return json.loads(message_data)
        return None

    def get_chat_messages(
        self, conversation_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict]:
        """Get messages for a conversation"""
        conversation_key = f"conversation:{conversation_id}:messages"

        # Get message IDs from sorted set (most recent first)
        message_ids = self.redis_client.zrevrange(conversation_key, offset, offset + limit - 1)

        messages = []
        for message_id in message_ids:
            message_data = self.get_message(message_id.decode("utf-8"))
            if message_data:
                messages.append(message_data)

        return messages

    def get_conversation_message_count(self, conversation_id: str) -> int:
        """Get total message count for a conversation"""
        conversation_key = f"conversation:{conversation_id}:messages"
        return self.redis_client.zcard(conversation_key)

    def delete_message(self, message_id: str) -> bool:
        """Delete a message"""
        message_data = self.get_message(message_id)
        if not message_data:
            return False

        # Remove from Redis
        message_key = f"message:{message_id}"
        self.redis_client.delete(message_key)

        # Remove from conversation message list
        conversation_id = message_data["conversation_id"]
        conversation_key = f"conversation:{conversation_id}:messages"
        self.redis_client.zrem(conversation_key, message_id)

        return True


# Create a singleton instance
redis_service = RedisMessageService()
