import json
import uuid
from datetime import datetime

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
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
        
        print(f"WebSocket connect: user_id={self.user_id}, user={self.user}")
        
        if isinstance(self.user, AnonymousUser) or not self.user:
            print("WebSocket connect: Anonymous user, closing")
            await self.close()
            return
            
        # Verify the user ID matches the authenticated user
        if str(self.user.id) != self.user_id:
            print(f"WebSocket connect: User ID mismatch, closing")
            await self.close()
            return
            
        self.user_group_name = f"user_{self.user_id}"
        
        # Join user group
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        
        print(f"WebSocket connect: Accepting connection for user {self.user_id}")
        await self.accept()
        
        # Notify other users that this user is online
        print(f"WebSocket connect: notifying online_users group")
        await self.channel_layer.group_send(
            "online_users",
            {
                "type": "user_online",
                "user_id": self.user_id,
                "user_data": await self.get_user_data(self.user),
            }
        )

    async def disconnect(self, close_code):
        print(f"WebSocket disconnect: user {self.user_id} disconnecting")
        
        # Leave user group
        await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        
        # Notify other users that this user is offline
        print(f"WebSocket disconnect: notifying online_users group")
        await self.channel_layer.group_send(
            "online_users",
            {
                "type": "user_offline",
                "user_id": self.user_id,
            }
        )

    async def receive(self, text_data):
        try:
            print(f"WebSocket receive: raw text_data={text_data}")
            data = json.loads(text_data)
            message_type = data.get("type")
            
            print(f"WebSocket receive: type={message_type}, data={data}")
            
            if message_type == "send_message":
                print("WebSocket receive: calling handle_send_message")
                await self.handle_send_message(data)
            elif message_type == "typing":
                print("WebSocket receive: calling handle_typing")
                await self.handle_typing(data)
            elif message_type == "stop_typing":
                print("WebSocket receive: calling handle_stop_typing")
                await self.handle_stop_typing(data)
            else:
                print(f"WebSocket unknown message type: {message_type}")
                
        except json.JSONDecodeError as e:
            print(f"WebSocket JSON decode error: {e}")
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))
        except Exception as e:
            print(f"WebSocket receive error: {e}")
            await self.send(text_data=json.dumps({"error": str(e)}))

    async def handle_send_message(self, data):
        conversation_id = data.get("conversation_id")
        content = data.get("content")
        
        print(f"WebSocket handle_send_message: conversation_id={conversation_id}, content={content}")
        
        if not conversation_id or not content:
            print("WebSocket error: Missing conversation_id or content")
            await self.send(text_data=json.dumps({"error": "Missing conversation_id or content"}))
            return
            
        # Get conversation and validate access
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            print("WebSocket error: Conversation not found")
            await self.send(text_data=json.dumps({"error": "Conversation not found"}))
            return
            
        # Check if user is part of this conversation
        if not await self.is_user_in_conversation(conversation, self.user):
            print("WebSocket error: Access denied")
            await self.send(text_data=json.dumps({"error": "Access denied"}))
            return
            
        # Create message in database and Redis
        message_data = await self.create_message(conversation, content)
        print(f"WebSocket message created: {message_data}")
        
        # Send to both users in the conversation
        other_user = await self.get_other_user(conversation, self.user)
        other_user_group = f"user_{other_user.id}"
        
        message_payload = {
            "type": "new_message",
            "conversation_id": str(conversation.id),
            "message": message_data,
        }
        
        print(f"WebSocket sending to groups: {self.user_group_name}, {other_user_group}")
        
        # Send to both users
        await self.channel_layer.group_send(self.user_group_name, message_payload)
        await self.channel_layer.group_send(other_user_group, message_payload)
        
        print(f"WebSocket handle_send_message: completed successfully")

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
            }
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
            }
        )

    # WebSocket event handlers
    async def new_message(self, event):
        print(f"WebSocket new_message: sending to user {self.user_id}")
        print(f"WebSocket new_message: event={event}")
        message_payload = {
            "type": "new_message",
            "conversation_id": event["conversation_id"],
            "message": event["message"],
        }
        print(f"WebSocket new_message: payload={message_payload}")
        await self.send(text_data=json.dumps(message_payload))
        print(f"WebSocket new_message: sent successfully")

    async def user_typing(self, event):
        print(f"WebSocket user_typing: sending to user {self.user_id}")
        await self.send(text_data=json.dumps({
            "type": "user_typing",
            "conversation_id": event["conversation_id"],
            "user_id": event["user_id"],
            "user_name": event["user_name"],
        }))

    async def user_stop_typing(self, event):
        print(f"WebSocket user_stop_typing: sending to user {self.user_id}")
        await self.send(text_data=json.dumps({
            "type": "user_stop_typing",
            "conversation_id": event["conversation_id"],
            "user_id": event["user_id"],
        }))

    async def user_online(self, event):
        print(f"WebSocket user_online: sending to user {self.user_id}")
        await self.send(text_data=json.dumps({
            "type": "user_online",
            "user_id": event["user_id"],
            "user_data": event["user_data"],
        }))

    async def user_offline(self, event):
        print(f"WebSocket user_offline: sending to user {self.user_id}")
        await self.send(text_data=json.dumps({
            "type": "user_offline",
            "user_id": event["user_id"],
        }))

    # Database sync methods
    @database_sync_to_async
    def get_user(self, user_id):
        try:
            print(f"WebSocket get_user: looking for user {user_id}")
            user = User.objects.get(id=user_id)
            print(f"WebSocket get_user: found {user}")
            return user
        except User.DoesNotExist:
            print(f"WebSocket get_user: not found {user_id}")
            return AnonymousUser()

    @database_sync_to_async
    def get_user_data(self, user):
        print(f"WebSocket get_user_data: getting data for {user}")
        data = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "username": user.username,
            "is_verified": user.is_verified,
        }
        print(f"WebSocket get_user_data: returning {data}")
        return data

    @database_sync_to_async
    def get_conversation(self, conversation_id):
        try:
            print(f"WebSocket get_conversation: looking for {conversation_id}")
            conversation = Conversation.objects.get(id=conversation_id)
            print(f"WebSocket get_conversation: found {conversation}")
            return conversation
        except Conversation.DoesNotExist:
            print(f"WebSocket get_conversation: not found {conversation_id}")
            return None

    @database_sync_to_async
    def is_user_in_conversation(self, conversation, user):
        result = conversation.user1 == user or conversation.user2 == user
        print(f"WebSocket is_user_in_conversation: {result} (user1={conversation.user1.id}, user2={conversation.user2.id}, current_user={user.id})")
        return result

    @database_sync_to_async
    def get_other_user(self, conversation, user):
        if conversation.user1 == user:
            other_user = conversation.user2
        else:
            other_user = conversation.user1
        print(f"WebSocket get_other_user: {other_user.id} (current_user={user.id})")
        return other_user

    async def create_message(self, conversation, content):
        print(f"WebSocket create_message: starting for conversation {conversation.id}")
        
        # Get other user first
        other_user = await self.get_other_user(conversation, self.user)
        
        # Store message in Redis
        print(f"WebSocket create_message: storing in Redis")
        message_id = redis_service.store_message(
            conversation_id=str(conversation.id),
            sender_id=str(self.user.id),
            receiver_id=str(other_user.id),
            content=content,
        )
        print(f"WebSocket create_message: stored in Redis with ID {message_id}")
        
        # Create message metadata
        print(f"WebSocket create_message: creating metadata")
        message = await self.create_message_metadata(conversation, other_user, message_id)
        
        # Update conversation timestamp
        print(f"WebSocket create_message: updating timestamp")
        await self.update_conversation_timestamp(conversation)
        
        result = {
            "id": message_id,
            "conversation_id": str(conversation.id),
            "sender_id": str(self.user.id),
            "receiver_id": str(other_user.id),
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        print(f"WebSocket create_message: returning {result}")
        return result
    
    @database_sync_to_async
    def create_message_metadata(self, conversation, other_user, message_id):
        print(f"WebSocket create_message_metadata: creating message {message_id}")
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            receiver=other_user,
            message_id=message_id,
        )
        print(f"WebSocket create_message_metadata: created {message}")
        return message
    
    @database_sync_to_async
    def update_conversation_timestamp(self, conversation):
        print(f"WebSocket update_conversation_timestamp: updating {conversation.id}")
        conversation.save()
        print(f"WebSocket update_conversation_timestamp: updated {conversation.id}")