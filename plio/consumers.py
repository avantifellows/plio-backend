import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

# from users.serializers import UserSerializer


class UserConsumer(WebsocketConsumer):
    """
    Defines a general consumer for the User model
    """

    def connect(self):
        self.group_name = "users"
        # Join users group
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        # accept the connection
        self.accept()

    def disconnect(self, close_code):
        # Leave users group
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name, self.channel_name
        )

    def receive(self, data):
        # the websocket doesn't recieve anything currently
        pass

    def send_user(self, event):
        # serialize the recieved User instance
        # and send it over the websocket
        user_data = event["data"]
        self.send(json.dumps({"user": user_data}))
