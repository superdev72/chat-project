"""
ASGI config for chat_project project.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chat_project.settings")

# Initialize Django
import django  # noqa: E402

django.setup()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from django.core.asgi import get_asgi_application  # noqa: E402

from apps.chat.middleware import TokenAuthMiddleware  # noqa: E402
from apps.chat.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": TokenAuthMiddleware(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
    }
)
