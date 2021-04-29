# Details about what this is and why this file is needed -
# https://channels.readthedocs.io/en/latest/asgi.html#
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import plio.urls

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plio.settings")

application = ProtocolTypeRouter(
    {
        # handle http/https requests
        "http": get_asgi_application(),
        # handle ws/wss requests
        "websocket": AuthMiddlewareStack(URLRouter(plio.urls.websocket_urlpatterns)),
    }
)
