import uuid

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Conversation(models.Model):
    """Represents a conversation between two users"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user1 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversations_as_user1"
    )
    user2 = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversations_as_user2"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conversations"
        unique_together = ["user1", "user2"]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(user1=models.F("user2")), name="no_self_conversation"
            )
        ]

    def __str__(self):
        return f"Conversation between {self.user1.email} and {self.user2.email}"

    @classmethod
    def get_or_create_conversation(cls, user1, user2):
        """Get or create a conversation between two users"""
        # Ensure consistent ordering (smaller ID first)
        if user1.id > user2.id:
            user1, user2 = user2, user1

        conversation, created = cls.objects.get_or_create(user1=user1, user2=user2)
        return conversation, created

    def get_other_user(self, current_user):
        """Get the other user in the conversation"""
        if current_user == self.user1:
            return self.user2
        return self.user1


class Message(models.Model):
    """Stores message metadata (actual content is in Redis)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="received_messages"
    )
    message_id = models.CharField(max_length=255, unique=True)  # Redis key
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = "messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"Message from {self.sender.email} to {self.receiver.email}"
