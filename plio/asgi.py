# Details about what this is and why this file is needed -
# https://channels.readthedocs.io/en/latest/asgi.html#
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plio.settings")

# Initialize Django ASGI application early to ensure the AppRegistry is
# populated before importing Channels routing or any project modules.
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
import plio.urls  # noqa: E402

application = ProtocolTypeRouter(
    {
        # handle http/https requests
        "http": django_asgi_app,
        # handle ws/wss requests
        "websocket": AuthMiddlewareStack(URLRouter(plio.urls.websocket_urlpatterns)),
    }
)
