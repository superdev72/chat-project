from unittest.mock import MagicMock, patch

from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chat.models import Conversation, Message
from apps.chat.services import RedisMessageService

User = get_user_model()


class ConversationTestCase(APITestCase):
    """Test cases for conversation functionality"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            username="user1",
            password="password123",
            first_name="User",
            last_name="One",
            is_verified=True,
        )

        self.user2 = User.objects.create_user(
            email="user2@example.com",
            username="user2",
            password="password123",
            first_name="User",
            last_name="Two",
            is_verified=True,
        )

        self.user3 = User.objects.create_user(
            email="user3@example.com",
            username="user3",
            password="password123",
            first_name="User",
            last_name="Three",
            is_verified=True,
        )

        # Create conversation with proper ordering (smaller ID first)
        if self.user1.id < self.user2.id:
            self.conversation = Conversation.objects.create(user1=self.user1, user2=self.user2)
        else:
            self.conversation = Conversation.objects.create(user1=self.user2, user2=self.user1)

        self.client.force_authenticate(user=self.user1)

    def test_create_conversation(self):
        """Test creating a conversation"""
        response = self.client.post(f"/api/chat/conversations/{self.user3.id}/")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)

        # Check if conversation was created
        conversation = Conversation.objects.get(id=response.data["id"])
        # Users are ordered by ID (smaller first)
        if self.user1.id < self.user3.id:
            self.assertEqual(conversation.user1, self.user1)
            self.assertEqual(conversation.user2, self.user3)
        else:
            self.assertEqual(conversation.user1, self.user3)
            self.assertEqual(conversation.user2, self.user1)

    def test_create_existing_conversation(self):
        """Test creating a conversation that already exists"""
        response = self.client.post(f"/api/chat/conversations/{self.user2.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.conversation.id))

    def test_create_conversation_with_self(self):
        """Test creating a conversation with yourself"""
        response = self.client.post(f"/api/chat/conversations/{self.user1.id}/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_conversations(self):
        """Test listing conversations for authenticated user"""
        response = self.client.get("/api/chat/conversations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.conversation.id))

    def test_get_conversation_detail(self):
        """Test getting conversation detail"""
        detail_url = f"/api/chat/conversations/{self.user2.id}/"
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.conversation.id))


class MessageTestCase(APITestCase):
    """Test cases for message functionality"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            username="user1",
            password="password123",
            first_name="User",
            last_name="One",
            is_verified=True,
        )

        self.user2 = User.objects.create_user(
            email="user2@example.com",
            username="user2",
            password="password123",
            first_name="User",
            last_name="Two",
            is_verified=True,
        )

        self.conversation = Conversation.objects.create(user1=self.user1, user2=self.user2)

        self.client.force_authenticate(user=self.user1)

    @patch("apps.chat.services.RedisMessageService.store_message")
    def test_send_message(self, mock_store_message):
        """Test sending a message"""
        mock_store_message.return_value = "test-message-id"

        send_url = f"/api/chat/conversations/{self.conversation.id}/send/"
        data = {"content": "Hello, World!"}

        response = self.client.post(send_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)

        # Check if message metadata was created
        message = Message.objects.get(message_id="test-message-id")
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.conversation, self.conversation)

    def test_send_message_empty_content(self):
        """Test sending a message with empty content"""
        send_url = f"/api/chat/conversations/{self.conversation.id}/send/"
        data = {"content": ""}

        response = self.client.post(send_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    def test_send_message_unauthorized_user(self):
        """Test sending a message by unauthorized user"""
        user3 = User.objects.create_user(
            email="user3@example.com",
            username="user3",
            password="password123",
            first_name="User",
            last_name="Three",
            is_verified=True,
        )

        self.client.force_authenticate(user=user3)

        send_url = f"/api/chat/conversations/{self.conversation.id}/send/"
        data = {"content": "Hello, World!"}

        response = self.client.post(send_url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.chat.services.RedisMessageService.get_chat_messages")
    def test_get_messages(self, mock_get_messages):
        """Test getting messages from a conversation"""
        mock_messages = [
            {
                "id": "msg1",
                "sender_id": str(self.user1.id),
                "receiver_id": str(self.user2.id),
                "content": "Hello!",
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "id": "msg2",
                "sender_id": str(self.user2.id),
                "receiver_id": str(self.user1.id),
                "content": "Hi there!",
                "timestamp": "2024-01-01T00:01:00Z",
            },
        ]
        mock_get_messages.return_value = mock_messages

        messages_url = f"/api/chat/conversations/{self.conversation.id}/messages/"
        response = self.client.get(messages_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_messages_with_pagination(self):
        """Test getting messages with pagination"""
        messages_url = f"/api/chat/conversations/{self.conversation.id}/messages/"
        response = self.client.get(messages_url, {"limit": 10, "offset": 0})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)


class UserListTestCase(APITestCase):
    """Test cases for user list functionality"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            username="user1",
            password="password123",
            first_name="User",
            last_name="One",
            is_verified=True,
        )

        self.user2 = User.objects.create_user(
            email="user2@example.com",
            username="user2",
            password="password123",
            first_name="User",
            last_name="Two",
            is_verified=True,
        )

        self.unverified_user = User.objects.create_user(
            email="unverified@example.com",
            username="unverified",
            password="password123",
            first_name="Unverified",
            last_name="User",
            is_verified=False,
        )

        self.client.force_authenticate(user=self.user1)

    def test_list_users(self):
        """Test listing verified users"""
        response = self.client.get("/api/chat/users/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)  # user2 (user1 is excluded)

        # Check that unverified user is not included
        user_emails = [user["email"] for user in response.data["results"]]
        self.assertNotIn("unverified@example.com", user_emails)
        self.assertNotIn("user1@example.com", user_emails)  # Current user excluded

    def test_search_users(self):
        """Test searching users by email"""
        response = self.client.get("/api/chat/users/", {"search": "user2"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["email"], "user2@example.com")


class RedisMessageServiceTestCase(TestCase):
    """Test cases for Redis message service"""

    def setUp(self):
        self.redis_service = RedisMessageService()

    @patch("apps.chat.services.redis.from_url")
    def test_store_message(self, mock_redis):
        """Test storing a message in Redis"""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        # Create a new service instance with mocked Redis
        from apps.chat.services import RedisMessageService

        service = RedisMessageService()
        service.redis_client = mock_client

        message_id = service.store_message(
            conversation_id="test-conversation-id",
            sender_id="test-sender-id",
            receiver_id="test-receiver-id",
            content="Test message",
        )

        self.assertIsNotNone(message_id)
        mock_client.setex.assert_called()
        mock_client.zadd.assert_called()

    @patch("apps.chat.services.redis.from_url")
    def test_get_message(self, mock_redis):
        """Test getting a message from Redis"""
        mock_client = MagicMock()
        mock_client.get.return_value = '{"message_id": "test", "content": "test"}'
        mock_redis.return_value = mock_client

        # Create a new service instance with mocked Redis
        from apps.chat.services import RedisMessageService

        service = RedisMessageService()
        service.redis_client = mock_client

        message = service.get_message("test-message-id")

        self.assertIsNotNone(message)
        self.assertEqual(message["message_id"], "test")
        self.assertEqual(message["content"], "test")
