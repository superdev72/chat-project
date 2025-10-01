from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from django.conf import settings
from django.contrib.auth import login
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import User
from .serializers import (
    EmailVerificationSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send verification email
        self.send_verification_email(user)

        return Response(
            {
                "message": (
                    "User created successfully. Please check your email "
                    "for verification."
                ),
                "user_id": str(user.id),
            },
            status=status.HTTP_201_CREATED,
        )

    def send_verification_email(self, user):
        """Send verification email to user"""
        try:
            verification_url = (
                f"{settings.SITE_URL}/api/auth/verify-email/{user.verification_token}/"
            )

            html_message = render_to_string(
                "emails/verification_email.html",
                {
                    "user": user,
                    "verification_url": verification_url,
                },
            )

            plain_message = strip_tags(html_message)

            send_mail(
                subject="Verify Your Email - Chat Application",
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL or "noreply@chatapp.com",
                recipient_list=[user.email],
                fail_silently=True,  # Don't fail registration if email fails
            )
        except Exception as e:
            # Log the error but don't fail the registration
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to send verification email to {user.email}: {e}")


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """User login endpoint"""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        login(request, user)

        return Response(
            {
                "message": "Login successful",
                "token": token.key,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Get user profile"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def verify_email_view(request, token):
    """Email verification endpoint"""
    serializer = EmailVerificationSerializer(data={"token": token})
    if serializer.is_valid():
        user = User.objects.get(verification_token=token)
        user.is_verified = True
        user.save()

        # For GET requests (clicking email links), return HTML page
        if request.method == "GET":
            from django.shortcuts import render

            return render(
                request,
                "emails/verification_success.html",
                {
                    "user": user,
                    "message": (
                        "Email verified successfully! You can now log in "
                        "to your account."
                    ),
                },
            )

        # For POST requests (API calls), return JSON
        return Response(
            {"message": "Email verified successfully"}, status=status.HTTP_200_OK
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resend_verification_email_view(request):
    """Resend verification email"""
    user = request.user
    if user.is_verified:
        return Response(
            {"message": "Email is already verified"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Generate new token and send email
    user.generate_new_verification_token()

    verification_url = (
        f"{settings.SITE_URL}/api/auth/verify-email/{user.verification_token}/"
    )

    html_message = render_to_string(
        "emails/verification_email.html",
        {
            "user": user,
            "verification_url": verification_url,
        },
    )

    plain_message = strip_tags(html_message)

    send_mail(
        subject="Verify Your Email - Chat Application",
        message=plain_message,
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL or "noreply@chatapp.com",
        recipient_list=[user.email],
        fail_silently=False,
    )

    return Response(
        {"message": "Verification email sent successfully"}, status=status.HTTP_200_OK
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout endpoint"""
    try:
        # Delete the user's token
        request.user.auth_token.delete()
    except Exception:
        # Token might not exist, that's okay
        pass

    return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
