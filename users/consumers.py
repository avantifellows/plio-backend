import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer


class UserConsumer(WebsocketConsumer):
    """
    Defines a general consumer for a single User
    """

    def connect(self):
        # retrieve the user id from the url route
        # create a new group name for that specific user using the user_id
        # join the created group
        # accept the connection

        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.user_group_name = "user_%s" % self.user_id
        async_to_sync(self.channel_layer.group_add)(
            self.user_group_name, self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        # Leave the user group
        async_to_sync(self.channel_layer.group_discard)(
            self.user_group_name, self.channel_name
        )

    def receive(self, data):
        # the websocket doesn't recieve anything currently from the client
        pass

    def send_user(self, event):
        # send the recieved User data over the websocket
        user = event["data"]
        self.send(json.dumps({"user": user}))
