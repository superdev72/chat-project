from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from rest_framework.authtoken.models import Token

from django.contrib.auth.models import AnonymousUser


class TokenAuthMiddleware:
    """
    Custom middleware to authenticate WebSocket connections using token authentication
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Get token from query parameters
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token_key = query_params.get("token", [None])[0]

        user = await self.get_user_from_token(token_key)

        # Add user to scope
        scope["user"] = user

        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user_from_token(self, token_key):
        """Get user from token key"""
        if not token_key:
            return AnonymousUser()

        try:
            token = Token.objects.get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return AnonymousUser()
