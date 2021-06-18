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
from plio.models import Plio, Video, Item, Question, Image


class BaseTestCase(APITestCase):
    """Base class that sets up generic pre-requisites for all further test classes"""

    def setUp(self):
        self.client = APIClient()

        # User access and refresh tokens require an OAuth Provider application to be set up and use it as a foreign key.
        # As the test database is empty, we create an application instance before running the test cases.
        self.application = Application.objects.create(
            name=API_APPLICATION_NAME,
            redirect_uris="",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )

        # create a user
        self.user = User.objects.create(mobile="+919876543210")

        # set up access token for the user
        self.access_token = get_new_access_token(self.user, self.application)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.access_token.token)


def get_new_access_token(user, application):
    """Creates a new access token for the given user and application"""
    random_token = "".join(random.choices(string.ascii_lowercase, k=30))
    expire_seconds = OAUTH2_PROVIDER["ACCESS_TOKEN_EXPIRE_SECONDS"]
    scopes = " ".join(OAUTH2_PROVIDER["DEFAULT_SCOPES"])
    expires = timezone.now() + datetime.timedelta(seconds=expire_seconds)

    return AccessToken.objects.create(
        user=user,
        application=application,
        token=random_token,
        expires=expires,
        scope=scopes,
    )


class PlioTestCase(BaseTestCase):
    """Tests the Plio CRUD functionality."""

    def setUp(self):
        super().setUp()
        # seed a video
        self.video = Video.objects.create(
            title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )
        # seed some plios
        self.plio_1 = Plio.objects.create(
            name="Plio 1", video=self.video, created_by=self.user
        )
        self.plio_2 = Plio.objects.create(
            name="Plio 2", video=self.video, created_by=self.user
        )

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

    def test_guest_cannot_list_plio_uuids(self):
        # unset the credentials
        self.client.credentials()
        # get plio uuids
        response = self.client.get("/api/v1/plios/list_uuid/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list_empty_plio_uuids(self):
        """Test valid user listing plio uuids when they have no plios"""
        new_user = User.objects.create(mobile="+919988776655")
        new_access_token = get_new_access_token(new_user, self.application)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + new_access_token.token)
        # get plio uuids
        response = self.client.get("/api/v1/plios/list_uuid/")
        self.assertEqual(
            response.data,
            {
                "count": 0,
                "page_size": 5,
                "next": None,
                "previous": None,
                "results": [],
            },
        )

    def test_user_list_plio_uuids(self):
        """Test valid user listing plio uuids when they have plios"""
        # get plio uuids
        response = self.client.get("/api/v1/plios/list_uuid/")

        self.assertEqual(
            response.data,
            {
                "count": 2,
                "page_size": 5,
                "next": None,
                "previous": None,
                "results": [self.plio_2.uuid, self.plio_1.uuid],
            },
        )

    def test_user_can_duplicate_their_plio(self):
        plio = Plio.objects.filter(created_by=self.user).first()
        # duplicate plio
        response = self.client.post(f"/api/v1/plios/{plio.uuid}/duplicate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertNotEqual(plio.id, response.data["id"])
        self.assertNotEqual(plio.uuid, response.data["uuid"])
        self.assertEqual(plio.name, response.data["name"])

    def test_user_cannot_duplicate_other_user_plio(self):
        # create a new user
        new_user = User.objects.create(mobile="+919988776655")
        # create plio from the new user
        plio = Plio.objects.create(
            name="Plio New User", video=self.video, created_by=new_user
        )

        # duplicate plio
        response = self.client.post(f"/api/v1/plios/{plio.uuid}/duplicate/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class VideoTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        # seed some videos
        Video.objects.create(
            title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )
        Video.objects.create(
            title="Video 2", url="https://www.youtube.com/watch?v=jWdA2JFCxGw"
        )

    def test_guest_cannot_list_videos(self):
        # unset the credentials
        self.client.credentials()
        # get videos
        response = self.client.get(reverse("videos-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_list_videos(self):
        # get videos
        response = self.client.get(reverse("videos-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class ItemTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_for_item(self):
        # write API calls here
        self.assertTrue(True)


class QuestionTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_for_question(self):
        # write API calls here
        self.assertTrue(True)


class ImageTestCase(BaseTestCase):
    """Tests the Image CRUD functionality."""

    def setUp(self):
        super().setUp()
        # seed a video
        self.video = Video.objects.create(
            title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )
        # seed a plio, item and question
        self.test_plio = Plio.objects.create(
            name="test_plio", video=self.video, created_by=self.user
        )
        self.test_item = Item.objects.create(
            plio=self.test_plio, type="question", time=1
        )
        self.test_question = Question.objects.create(item=self.test_item)

    def test_user_can_attach_images_to_their_question(self):
        """
        Tests whether a user can link images to the questions
        that were created by themselves
        """
        # upload a test image and retrieve the id
        with open("plio/static/plio/test_image.jpeg", "rb") as img:
            response = self.client.post(reverse("images-list"), {"url": img})
        uploaded_image_id = response.json()["id"]

        # update the question with the newly uploaded image
        response = self.client.put(
            reverse("questions-detail", args=[self.test_question.id]),
            {"item": self.test_item.id, "image": uploaded_image_id},
        )
        # the user should be able to update the question
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_cannot_attach_image_to_other_user_question(self):
        """
        Tests that a user should NOT be able to link images to
        the questions that were created by some other user
        """
        # create a new user
        new_user = User.objects.create(mobile="+919988776654")

        # set up access token for the new user
        random_token = "".join(random.choices(string.ascii_lowercase, k=30))
        expire_seconds = OAUTH2_PROVIDER["ACCESS_TOKEN_EXPIRE_SECONDS"]
        scopes = " ".join(OAUTH2_PROVIDER["DEFAULT_SCOPES"])
        expires = timezone.now() + datetime.timedelta(seconds=expire_seconds)
        new_access_token = AccessToken.objects.create(
            user=new_user,
            application=self.application,
            token=random_token,
            expires=expires,
            scope=scopes,
        )
        # reset and set the new credentials
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + new_access_token.token)

        # create a new image entry using a test image
        with open("plio/static/plio/test_image.jpeg", "rb") as img:
            response = self.client.post(reverse("images-list"), {"url": img})

        # try updating the other user's question entry with
        # the newly created image
        uploaded_image_id = response.json()["id"]
        response = self.client.put(
            reverse("questions-detail", args=[self.test_question.id]),
            {"item": self.test_item.id, "image": uploaded_image_id},
        )
        # the user should not be able to link an image to
        # a question created by some other user
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_can_upload_image(self):
        """
        Tests whether an authorized user can create/upload an image
        """
        with open("plio/static/plio/test_image.jpeg", "rb") as img:
            response = self.client.post(reverse("images-list"), {"url": img})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_guest_cannot_upload_image(self):
        """
        Tests whether a guest(unauthorized user) should
        not be able to create/upload an image
        """
        # resetting the credentials to mock a guest user
        self.client.credentials()

        with open("plio/static/plio/test_image.jpeg", "rb") as img:
            response = self.client.post(reverse("images-list"), {"url": img})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_size_does_not_exceed_limit(self):
        """
        Tests whether any uploads more than
        `settings.DATA_UPLOAD_MAX_MEMORY_SIZE` should not be allowed
        """
        with open("plio/static/plio/test_image_10mb.jpeg", "rb") as img:
            response = self.client.post(reverse("images-list"), {"url": img})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_each_image_has_unique_name(self):
        """
        Tests whether each image entry when generated, has a unique name
        and should not conflict with a name that already exists
        """
        random.seed(10)
        test_image_1 = Image.objects.create()
        random.seed(10)
        test_image_2 = Image.objects.create()
        self.assertNotEqual(test_image_1.url.name, test_image_2.url.name)
