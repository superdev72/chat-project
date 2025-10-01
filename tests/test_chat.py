from unittest.mock import MagicMock, patch

from rest_framework import status
from rest_framework.test import APITestCase

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.chat.models import ChatRoom, Message
from apps.chat.services import RedisMessageService

User = get_user_model()


class ChatRoomTestCase(APITestCase):
    """Test cases for chat room functionality"""

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

        self.chat_room_url = reverse("chat-room-list-create")
        self.client.force_authenticate(user=self.user1)

    def test_create_chat_room(self):
        """Test creating a chat room"""
        data = {
            "name": "Test Chat Room",
            "participant_emails": ["user2@example.com", "user3@example.com"],
        }

        response = self.client.post(self.chat_room_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)

        # Check if chat room was created
        chat_room = ChatRoom.objects.get(id=response.data["id"])
        self.assertEqual(chat_room.name, data["name"])
        self.assertEqual(chat_room.created_by, self.user1)
        self.assertEqual(chat_room.participants.count(), 3)  # creator + 2 participants

    def test_create_chat_room_without_participants(self):
        """Test creating a chat room without additional participants"""
        data = {"name": "Solo Chat Room"}

        response = self.client.post(self.chat_room_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check if chat room was created with only creator
        chat_room = ChatRoom.objects.get(id=response.data["id"])
        self.assertEqual(chat_room.participants.count(), 1)
        self.assertIn(self.user1, chat_room.participants.all())

    def test_create_chat_room_with_invalid_participants(self):
        """Test creating a chat room with invalid participants"""
        data = {
            "name": "Test Chat Room",
            "participant_emails": ["nonexistent@example.com"],
        }

        response = self.client.post(self.chat_room_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("participant_emails", response.data)

    def test_list_chat_rooms(self):
        """Test listing chat rooms for authenticated user"""
        # Create a chat room
        chat_room = ChatRoom.objects.create(name="Test Room", created_by=self.user1)
        chat_room.participants.add(self.user1, self.user2)

        response = self.client.get(self.chat_room_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Test Room")

    def test_get_chat_room_detail(self):
        """Test getting chat room detail"""
        chat_room = ChatRoom.objects.create(name="Test Room", created_by=self.user1)
        chat_room.participants.add(self.user1, self.user2)

        detail_url = reverse("chat-room-detail", kwargs={"pk": chat_room.id})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Room")
        self.assertEqual(len(response.data["participants_info"]), 2)


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

        self.chat_room = ChatRoom.objects.create(
            name="Test Room", created_by=self.user1
        )
        self.chat_room.participants.add(self.user1, self.user2)

        self.client.force_authenticate(user=self.user1)

    @patch("apps.chat.services.RedisMessageService.store_message")
    def test_send_message(self, mock_store_message):
        """Test sending a message"""
        mock_store_message.return_value = "test-message-id"

        send_url = reverse("send-message", kwargs={"chat_room_id": self.chat_room.id})
        data = {"content": "Hello, World!"}

        response = self.client.post(send_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message_id", response.data)

        # Check if message metadata was created
        message = Message.objects.get(message_id="test-message-id")
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.chat_room, self.chat_room)

    def test_send_message_empty_content(self):
        """Test sending a message with empty content"""
        send_url = reverse("send-message", kwargs={"chat_room_id": self.chat_room.id})
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

        send_url = reverse("send-message", kwargs={"chat_room_id": self.chat_room.id})
        data = {"content": "Hello, World!"}

        response = self.client.post(send_url, data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("apps.chat.services.RedisMessageService.get_chat_messages")
    def test_get_messages(self, mock_get_messages):
        """Test getting messages from a chat room"""
        mock_messages = [
            {
                "message_id": "msg1",
                "sender_id": str(self.user1.id),
                "sender_name": self.user1.full_name,
                "content": "Hello!",
                "timestamp": "2024-01-01T00:00:00Z",
                "chat_room_id": str(self.chat_room.id),
            },
            {
                "message_id": "msg2",
                "sender_id": str(self.user2.id),
                "sender_name": self.user2.full_name,
                "content": "Hi there!",
                "timestamp": "2024-01-01T00:01:00Z",
                "chat_room_id": str(self.chat_room.id),
            },
        ]
        mock_get_messages.return_value = mock_messages

        messages_url = reverse(
            "get-messages", kwargs={"chat_room_id": self.chat_room.id}
        )
        response = self.client.get(messages_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["messages"]), 2)
        self.assertEqual(response.data["count"], 2)

    def test_get_messages_with_pagination(self):
        """Test getting messages with pagination"""
        messages_url = reverse(
            "get-messages", kwargs={"chat_room_id": self.chat_room.id}
        )
        response = self.client.get(messages_url, {"limit": 10, "offset": 0})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("messages", response.data)
        self.assertIn("count", response.data)
        self.assertIn("total_count", response.data)


class ParticipantManagementTestCase(APITestCase):
    """Test cases for participant management"""

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

        self.chat_room = ChatRoom.objects.create(
            name="Test Room", created_by=self.user1
        )
        self.chat_room.participants.add(self.user1, self.user2)

        self.client.force_authenticate(user=self.user1)

    def test_add_participant(self):
        """Test adding a participant to chat room"""
        add_url = reverse("add-participant", kwargs={"chat_room_id": self.chat_room.id})
        data = {"email": "user3@example.com"}

        response = self.client.post(add_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if participant was added
        self.chat_room.refresh_from_db()
        self.assertIn(self.user3, self.chat_room.participants.all())

    def test_add_existing_participant(self):
        """Test adding an existing participant"""
        add_url = reverse("add-participant", kwargs={"chat_room_id": self.chat_room.id})
        data = {"email": "user2@example.com"}

        response = self.client.post(add_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_remove_participant(self):
        """Test removing a participant from chat room"""
        remove_url = reverse(
            "remove-participant",
            kwargs={"chat_room_id": self.chat_room.id, "user_id": self.user2.id},
        )

        response = self.client.delete(remove_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if participant was removed
        self.chat_room.refresh_from_db()
        self.assertNotIn(self.user2, self.chat_room.participants.all())

    def test_remove_creator(self):
        """Test removing chat room creator"""
        remove_url = reverse(
            "remove-participant",
            kwargs={"chat_room_id": self.chat_room.id, "user_id": self.user1.id},
        )

        response = self.client.delete(remove_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)


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
            chat_room_id="test-room-id",
            sender_id="test-sender-id",
            sender_name="Test Sender",
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
