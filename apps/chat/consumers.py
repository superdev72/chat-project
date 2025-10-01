import json
from datetime import datetime

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from apps.chat.models import Conversation, Message
from apps.chat.services import redis_service

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]

        # Get user from scope (set by AuthMiddlewareStack)
        self.user = self.scope.get("user")

        if isinstance(self.user, AnonymousUser) or not self.user:
            await self.close()
            return

        # Verify the user ID matches the authenticated user
        if str(self.user.id) != self.user_id:
            await self.close()
            return

        self.user_group_name = f"user_{self.user_id}"

        # Join user group
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        await self.accept()

        # Notify other users that this user is online
        await self.channel_layer.group_send(
            "online_users",
            {
                "type": "user_online",
                "user_id": self.user_id,
                "user_data": await self.get_user_data(self.user),
            },
        )

    async def disconnect(self, close_code):
        # Leave user group
        await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

        # Notify other users that this user is offline
        await self.channel_layer.group_send(
            "online_users",
            {
                "type": "user_offline",
                "user_id": self.user_id,
            },
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "send_message":
                await self.handle_send_message(data)
            elif message_type == "typing":
                await self.handle_typing(data)
            elif message_type == "stop_typing":
                await self.handle_stop_typing(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))

    async def handle_send_message(self, data):
        conversation_id = data.get("conversation_id")
        content = data.get("content")

        if not conversation_id or not content:
            await self.send(
                text_data=json.dumps({"error": "Missing conversation_id or content"})
            )
            return

        # Get conversation and validate access
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            await self.send(text_data=json.dumps({"error": "Conversation not found"}))
            return

        # Check if user is part of this conversation
        if not await self.is_user_in_conversation(conversation, self.user):
            await self.send(text_data=json.dumps({"error": "Access denied"}))
            return

        # Create message in database and Redis
        message_data = await self.create_message(conversation, content)

        # Send to both users in the conversation
        other_user = await self.get_other_user(conversation, self.user)
        other_user_group = f"user_{other_user.id}"

        message_payload = {
            "type": "new_message",
            "conversation_id": str(conversation.id),
            "message": message_data,
        }

        # Send to both users
        await self.channel_layer.group_send(self.user_group_name, message_payload)
        await self.channel_layer.group_send(other_user_group, message_payload)

    async def handle_typing(self, data):
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            return

        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return

        other_user = await self.get_other_user(conversation, self.user)
        other_user_group = f"user_{other_user.id}"

        await self.channel_layer.group_send(
            other_user_group,
            {
                "type": "user_typing",
                "conversation_id": conversation_id,
                "user_id": self.user_id,
                "user_name": self.user.full_name,
            },
        )

    async def handle_stop_typing(self, data):
        conversation_id = data.get("conversation_id")
        if not conversation_id:
            return

        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return

        other_user = await self.get_other_user(conversation, self.user)
        other_user_group = f"user_{other_user.id}"

        await self.channel_layer.group_send(
            other_user_group,
            {
                "type": "user_stop_typing",
                "conversation_id": conversation_id,
                "user_id": self.user_id,
            },
        )

    # WebSocket event handlers
    async def new_message(self, event):
        message_payload = {
            "type": "new_message",
            "conversation_id": event["conversation_id"],
            "message": event["message"],
        }
        await self.send(text_data=json.dumps(message_payload))

    async def user_typing(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_typing",
                    "conversation_id": event["conversation_id"],
                    "user_id": event["user_id"],
                    "user_name": event["user_name"],
                }
            )
        )

    async def user_stop_typing(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_stop_typing",
                    "conversation_id": event["conversation_id"],
                    "user_id": event["user_id"],
                }
            )
        )

    async def user_online(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_online",
                    "user_id": event["user_id"],
                    "user_data": event["user_data"],
                }
            )
        )

    async def user_offline(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_offline",
                    "user_id": event["user_id"],
                }
            )
        )

    # Database sync methods
    @database_sync_to_async
    def get_user(self, user_id):
        try:
            user = User.objects.get(id=user_id)
            return user
        except User.DoesNotExist:
            return AnonymousUser()

    @database_sync_to_async
    def get_user_data(self, user):
        data = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "username": user.username,
            "is_verified": user.is_verified,
        }
        return data

    @database_sync_to_async
    def get_conversation(self, conversation_id):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            return conversation
        except Conversation.DoesNotExist:
            return None

    @database_sync_to_async
    def is_user_in_conversation(self, conversation, user):
        return conversation.user1 == user or conversation.user2 == user

    @database_sync_to_async
    def get_other_user(self, conversation, user):
        if conversation.user1 == user:
            return conversation.user2
        else:
            return conversation.user1

    async def create_message(self, conversation, content):
        # Get other user first
        other_user = await self.get_other_user(conversation, self.user)

        # Store message in Redis
        message_id = redis_service.store_message(
            conversation_id=str(conversation.id),
            sender_id=str(self.user.id),
            receiver_id=str(other_user.id),
            content=content,
        )

        # Create message metadata
        await self.create_message_metadata(conversation, other_user, message_id)

        # Update conversation timestamp
        await self.update_conversation_timestamp(conversation)

        result = {
            "id": message_id,
            "conversation_id": str(conversation.id),
            "sender_id": str(self.user.id),
            "receiver_id": str(other_user.id),
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return result

    @database_sync_to_async
    def create_message_metadata(self, conversation, other_user, message_id):
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            receiver=other_user,
            message_id=message_id,
        )
        return message

    @database_sync_to_async
    def update_conversation_timestamp(self, conversation):
        conversation.save()
