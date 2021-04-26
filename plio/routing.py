from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("api/v1/users/", consumers.UserConsumer.as_asgi()),
]
