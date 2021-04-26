import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import plio.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plio.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(plio.routing.websocket_urlpatterns)),
    }
)
