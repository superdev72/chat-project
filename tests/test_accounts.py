from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserRegistrationTestCase(APITestCase):
    """Test cases for user registration"""

    def setUp(self):
        self.register_url = reverse("user-register")
        self.valid_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "username": "johndoe",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
        }

    @patch("apps.accounts.views.UserRegistrationView.send_verification_email")
    def test_successful_registration(self, mock_send_email):
        """Test successful user registration"""
        response = self.client.post(self.register_url, self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        self.assertIn("user_id", response.data)

        # Check if user was created
        user = User.objects.get(email=self.valid_data["email"])
        self.assertEqual(user.first_name, self.valid_data["first_name"])
        self.assertEqual(user.last_name, self.valid_data["last_name"])
        self.assertFalse(user.is_verified)

        # Check if verification email was sent
        mock_send_email.assert_called_once()

    def test_registration_with_existing_email(self):
        """Test registration with existing email"""
        # Create a user first
        User.objects.create_user(
            email=self.valid_data["email"], username="existing", password="password123"
        )

        response = self.client.post(self.register_url, self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_registration_with_mismatched_passwords(self):
        """Test registration with mismatched passwords"""
        invalid_data = self.valid_data.copy()
        invalid_data["password_confirm"] = "differentpassword"

        response = self.client.post(self.register_url, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_registration_with_invalid_email(self):
        """Test registration with invalid email format"""
        invalid_data = self.valid_data.copy()
        invalid_data["email"] = "invalid-email"

        response = self.client.post(self.register_url, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)


class UserLoginTestCase(APITestCase):
    """Test cases for user login"""

    def setUp(self):
        self.login_url = reverse("user-login")
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="password123",
            first_name="Test",
            last_name="User",
            is_verified=True,
        )

    def test_successful_login(self):
        """Test successful login"""
        data = {"email": "test@example.com", "password": "password123"}

        response = self.client.post(self.login_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertIn("user", response.data)

    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {"email": "test@example.com", "password": "wrongpassword"}

        response = self.client.post(self.login_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_login_with_unverified_user(self):
        """Test login with unverified user"""
        self.user.is_verified = False
        self.user.save()

        data = {"email": "test@example.com", "password": "password123"}

        response = self.client.post(self.login_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)


class EmailVerificationTestCase(APITestCase):
    """Test cases for email verification"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="password123",
            first_name="Test",
            last_name="User",
            is_verified=False,
        )

    def test_successful_email_verification(self):
        """Test successful email verification"""
        verification_url = reverse(
            "verify-email", kwargs={"token": self.user.verification_token}
        )

        response = self.client.post(verification_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if user is now verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)

    def test_email_verification_with_invalid_token(self):
        """Test email verification with invalid token"""
        verification_url = reverse("verify-email", kwargs={"token": "invalid-token"})

        response = self.client.post(verification_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("token", response.data)

    def test_email_verification_already_verified(self):
        """Test email verification for already verified user"""
        self.user.is_verified = True
        self.user.save()

        verification_url = reverse(
            "verify-email", kwargs={"token": self.user.verification_token}
        )

        response = self.client.post(verification_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("token", response.data)


class UserProfileTestCase(APITestCase):
    """Test cases for user profile"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="password123",
            first_name="Test",
            last_name="User",
            is_verified=True,
        )
        self.profile_url = reverse("user-profile")

    def test_get_profile_authenticated(self):
        """Test getting profile for authenticated user"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["first_name"], self.user.first_name)
        self.assertEqual(response.data["last_name"], self.user.last_name)

    def test_get_profile_unauthenticated(self):
        """Test getting profile for unauthenticated user"""
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
