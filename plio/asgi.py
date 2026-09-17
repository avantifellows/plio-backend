# Details about what this is and why this file is needed -
# https://channels.readthedocs.io/en/latest/asgi.html#
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plio.settings")

# Initialize Django ASGI application early to ensure the AppRegistry is
# populated before importing Channels routing or any project modules.
from django.conf import settings  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
import plio.urls  # noqa: E402
from servestatic import ServeStaticASGI  # noqa: E402


def add_static_security_headers(headers, path, url):
    """Keep the MIME-sniffing protection normally supplied by Django."""
    headers["X-Content-Type-Options"] = "nosniff"


static_http_app = ServeStaticASGI(
    django_asgi_app,
    root=settings.STATIC_ROOT,
    prefix=settings.STATIC_URL,
    autorefresh=False,
    max_age=60,
    allow_unsafe_symlinks=False,
    add_headers_function=add_static_security_headers,
)

application = ProtocolTypeRouter(
    {
        # handle http/https requests
        "http": static_http_app,
        # handle ws/wss requests
        "websocket": AuthMiddlewareStack(URLRouter(plio.urls.websocket_urlpatterns)),
    }
)
