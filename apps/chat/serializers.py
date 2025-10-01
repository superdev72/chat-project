from rest_framework import serializers

from apps.accounts.models import User
from apps.chat.models import Conversation, Message


class UserSerializer(serializers.ModelSerializer):
    """Basic user information serializer"""

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "username", "is_verified")


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations"""

    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "other_user",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_other_user(self, obj):
        """Get the other user in the conversation"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            other_user = obj.get_other_user(request.user)
            return UserSerializer(other_user).data
        return None

    def get_last_message(self, obj):
        """Get the last message from Redis"""
        try:
            from apps.chat.services import redis_service

            messages = redis_service.get_chat_messages(obj.id, limit=1)
            if messages:
                return messages[0]
        except Exception:
            pass
        return None

    def get_unread_count(self, obj):
        """Get unread message count"""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.messages.filter(
                receiver=request.user, is_read=False, is_deleted=False
            ).count()
        return 0


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages"""

    sender_info = serializers.SerializerMethodField()
    receiver_info = serializers.SerializerMethodField()
    content = serializers.CharField(write_only=True)
    message_data = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id",
            "sender_info",
            "receiver_info",
            "content",
            "message_data",
            "created_at",
            "is_read",
        )
        read_only_fields = (
            "id",
            "created_at",
            "sender_info",
            "receiver_info",
            "message_data",
        )

    def get_sender_info(self, obj):
        """Get sender information"""
        return UserSerializer(obj.sender).data

    def get_receiver_info(self, obj):
        """Get receiver information"""
        return UserSerializer(obj.receiver).data

    def get_message_data(self, obj):
        """Get message data from Redis"""
        try:
            from apps.chat.services import redis_service

            return redis_service.get_message(obj.message_id)
        except Exception:
            return None

    def create(self, validated_data):
        """Create message and store in Redis"""
        conversation = validated_data["conversation"]
        sender = self.context["request"].user
        receiver = conversation.get_other_user(sender)
        content = validated_data["content"]

        # Store message in Redis
        from apps.chat.services import redis_service

        message_id = redis_service.store_message(
            conversation_id=str(conversation.id),
            sender_id=str(sender.id),
            receiver_id=str(receiver.id),
            content=content,
        )

        # Create message metadata
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            receiver=receiver,
            message_id=message_id,
        )

        return message


class MessageListSerializer(serializers.Serializer):
    """Serializer for deserializing messages from Redis"""

    id = serializers.CharField()
    sender_id = serializers.CharField()
    receiver_id = serializers.CharField()
    content = serializers.CharField()
    timestamp = serializers.DateTimeField()
