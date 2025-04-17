# Details about what this is and why this file is needed -
# https://channels.readthedocs.io/en/latest/asgi.html#
import os
import django

# Set environment before anything else
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plio.settings")

# Initialize Django before importing anything from it
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import plio.urls


application = ProtocolTypeRouter(
    {
        # handle http/https requests
        "http": get_asgi_application(),
        # handle ws/wss requests
        "websocket": AuthMiddlewareStack(URLRouter(plio.urls.websocket_urlpatterns)),
    }
)

# asgi.py is used to run the server using Daphne or any other ASGI server.
# pip install daphne
# Run the server using daphne
# daphne -b 0.0.0.0 -p 8000 plio.asgi:application