from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db import models
from django.shortcuts import get_object_or_404

from apps.accounts.models import User
from apps.chat.models import Conversation, Message
from apps.chat.serializers import (
    ConversationSerializer,
    MessageListSerializer,
    MessageSerializer,
    UserSerializer,
)
from apps.chat.services import redis_service


class UserListView(generics.ListAPIView):
    """List all verified users (excluding current user)"""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = User.objects.filter(is_verified=True).exclude(
            id=self.request.user.id
        )

        # Search functionality
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                models.Q(email__icontains=search)
                | models.Q(username__icontains=search)
                | models.Q(full_name__icontains=search)
            )

        return queryset.order_by("username")


class ConversationListView(generics.ListAPIView):
    """List all conversations for the current user"""

    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(
            models.Q(user1=self.request.user) | models.Q(user2=self.request.user)
        ).order_by("-updated_at")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def conversation_detail_view(request, user_id):
    """Get or create a conversation with a specific user"""

    if request.method == "GET":
        # Get existing conversation
        other_user = get_object_or_404(User, id=user_id, is_verified=True)
        conversation = Conversation.objects.filter(
            models.Q(user1=request.user, user2=other_user)
            | models.Q(user1=other_user, user2=request.user)
        ).first()

        if not conversation:
            return Response(
                {"error": "No conversation found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ConversationSerializer(conversation, context={"request": request})
        return Response(serializer.data)

    elif request.method == "POST":
        # Create new conversation
        other_user = get_object_or_404(User, id=user_id, is_verified=True)

        if other_user == request.user:
            return Response(
                {"error": "Cannot create conversation with yourself"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation, created = Conversation.get_or_create_conversation(
            request.user, other_user
        )
        serializer = ConversationSerializer(conversation, context={"request": request})

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_messages_view(request, conversation_id):
    """Get messages for a conversation"""

    conversation = get_object_or_404(Conversation, id=conversation_id)

    # Check if user is part of this conversation
    if conversation.user1 != request.user and conversation.user2 != request.user:
        return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

    # Get messages from Redis
    messages = redis_service.get_chat_messages(conversation_id)

    # Mark messages as read for the requesting user
    Message.objects.filter(
        conversation=conversation, receiver=request.user, is_read=False
    ).update(is_read=True)

    serializer = MessageListSerializer(messages, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_message_view(request, conversation_id):
    """Send a message in a conversation"""

    conversation = get_object_or_404(Conversation, id=conversation_id)

    # Check if user is part of this conversation
    if conversation.user1 != request.user and conversation.user2 != request.user:
        return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

    serializer = MessageSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        # Add conversation to validated data
        serializer.validated_data["conversation"] = conversation
        message = serializer.save()

        # Update conversation timestamp
        conversation.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_message_view(request, message_id):
    """Delete a message"""

    message = get_object_or_404(Message, message_id=message_id)

    # Check if user is the sender
    if message.sender != request.user:
        return Response({"error": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

    # Mark as deleted
    message.is_deleted = True
    message.save()

    # Delete from Redis
    redis_service.delete_message(message_id)

    return Response(
        {"message": "Message deleted successfully"}, status=status.HTTP_200_OK
    )
