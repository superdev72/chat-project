#!/usr/bin/env python
"""
Test script to verify the chat application setup
"""

import os
import sys

import django
from django.conf import settings


def test_setup():
    """Test the Django setup"""
    print("Testing Django setup...")

    # Set up Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chat_project.settings")
    django.setup()

    # Test database connection
    from django.db import connection

    try:
        connection.ensure_connection()
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

    # Test Redis connection
    try:
        import redis

        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        print("✓ Redis connection successful")
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False

    # Test models
    try:
        from apps.accounts.models import User  # noqa: F401
        from apps.chat.models import ChatRoom, Message  # noqa: F401

        print("✓ Models imported successfully")
    except Exception as e:
        print(f"✗ Model import failed: {e}")
        return False

    # Test services
    try:
        from apps.chat.services import RedisMessageService

        RedisMessageService()
        print("✓ Redis service initialized successfully")
    except Exception as e:
        print(f"✗ Redis service failed: {e}")
        return False

    print("\n✓ All tests passed! The setup is working correctly.")
    return True


if __name__ == "__main__":
    success = test_setup()
    sys.exit(0 if success else 1)
