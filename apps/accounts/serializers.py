from rest_framework import serializers

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "username",
            "password",
            "password_confirm",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists")
        return value

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""

    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError("Invalid credentials")
            if not user.is_verified:
                raise serializers.ValidationError(
                    "Please check your mailbox and verify your account "
                    "by clicking the link there."
                )
            attrs["user"] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include email and password")


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "is_verified", "created_at", "updated_at")


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification"""

    token = serializers.UUIDField()

    def validate_token(self, value):
        try:
            user = User.objects.get(verification_token=value)
            if user.is_verified:
                raise serializers.ValidationError("Email is already verified")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid verification token")
