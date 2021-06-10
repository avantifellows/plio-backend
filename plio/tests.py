import datetime
import random
import string
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from rest_framework import status
from oauth2_provider.models import Application
from oauth2_provider.models import AccessToken
from django.urls import reverse

from users.models import User
from plio.settings import API_APPLICATION_NAME, OAUTH2_PROVIDER
from plio.models import Plio, Video


class BaseTestCase(APITestCase):
    """Base class that sets up generic pre-requisites for all further test classes"""

    def setUp(self):
        self.client = APIClient()

        # User access and refresh tokens require an OAuth Provider application to be set up and use it as a foreign key.
        # As the test database is empty, we create an application instance before running the test cases.
        application = Application.objects.create(
            name=API_APPLICATION_NAME,
            redirect_uris="",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )

        # create a user
        self.user = User.objects.create(mobile="+919876543210")

        # set up access token for the user
        random_token = "".join(random.choices(string.ascii_lowercase, k=30))
        expire_seconds = OAUTH2_PROVIDER["ACCESS_TOKEN_EXPIRE_SECONDS"]
        scopes = " ".join(OAUTH2_PROVIDER["DEFAULT_SCOPES"])
        expires = timezone.now() + datetime.timedelta(seconds=expire_seconds)
        self.access_token = AccessToken.objects.create(
            user=self.user,
            application=application,
            token=random_token,
            expires=expires,
            scope=scopes,
        )
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.access_token.token)


class PlioCRUDTestCase(BaseTestCase):
    """Tests the Plio CRUD functionality."""

    def setUp(self):
        super().setUp()
        # seed a video
        self.video = Video.objects.create(
            title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )
        # seed some plios
        Plio.objects.create(name="Plio 1", video=self.video, created_by=self.user)
        Plio.objects.create(name="Plio 2", video=self.video, created_by=self.user)

    def test_guest_cannot_list_plios(self):
        # unset the credentials
        self.client.credentials()
        # get plios
        response = self.client.get(reverse("plios-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_list_plios(self):
        # get plios
        response = self.client.get(reverse("plios-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_user_list_own_plios(self):
        """A user should only be able to list their own plios"""
        # create a new user
        new_user = User.objects.create(mobile="+919988776655")
        # create plio from the new user
        Plio.objects.create(name="Plio 1", video=self.video, created_by=new_user)

        # get plios
        response = self.client.get(reverse("plios-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # the count should remain 2 as the new plio was created with different user
        self.assertEqual(response.data["count"], 2)


class VideoCRUDTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_for_video(self):
        # write API calls here
        self.assertTrue(True)


class ItemCRUDTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_for_item(self):
        # write API calls here
        self.assertTrue(True)


class QuestionCRUDTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_for_question(self):
        # write API calls here
        self.assertTrue(True)
