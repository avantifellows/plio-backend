import datetime
import random
import string
import json
from django.utils import timezone

from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from rest_framework import status
from oauth2_provider.models import Application
from oauth2_provider.models import AccessToken
from django.urls import reverse

# from django.db import connection

from users.models import User, Role
from organizations.models import Organization
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

        # create 2 users
        self.user = User.objects.create(mobile="+919876543210")
        self.user_2 = User.objects.create(mobile="+919988776655")

        # set up access token for the user
        self.access_token = get_new_access_token(self.user, self.application)
        self.access_token_2 = get_new_access_token(self.user_2, self.application)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.access_token.token)

        # create org
        self.organization = Organization.objects.create(name="Org 1", shortcode="org-1")

        # create roles
        self.org_view_role = Role.objects.filter(name="org-view").first()


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
        # create plio from a different user
        Plio.objects.create(name="Plio 1", video=self.video, created_by=self.user_2)

        # get plios
        response = self.client.get(reverse("plios-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # the count should remain 2 as the new plio was created with different user
        self.assertEqual(response.data["count"], 2)

    # def test_user_list_own_plios_in_org(self):
    #     """A user should be able to list their own plios in org workspace"""
    #     # add user to organization
    #     OrganizationUser.objects.create(
    #         organization=self.organization, user=self.user, role=self.org_view_role
    #     )

    #     # set db connection to organization schema
    #     connection.set_schema(self.organization.schema_name)

    #     # create video in the org workspace
    #     video_org = Video.objects.create(
    #         title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
    #     )

    #     # create plio within the org workspace
    #     plio_org = Plio.objects.create(
    #         name="Plio 1", video=video_org, created_by=self.user
    #     )

    #     # set organization in request
    #     self.client.credentials(
    #         HTTP_ORGANIZATION=self.organization.shortcode,
    #         HTTP_AUTHORIZATION="Bearer " + self.access_token.token,
    #     )

    #     # get plios
    #     response = self.client.get(reverse("plios-list"))

    #     # the plio created above should be listed
    #     self.assertEqual(len(response.data["results"]), 1)
    #     self.assertEqual(response.data["results"][0]["uuid"], plio_org.uuid)

    #     # reset the connection
    #     connection.set_schema("public")

    # def test_user_list_other_plios_in_org(self):
    #     """A user should be able to list plios created by others in org workspace"""
    #     # add users to organization
    #     OrganizationUser.objects.create(
    #         organization=self.organization, user=self.user, role=self.org_view_role
    #     )

    #     OrganizationUser.objects.create(
    #         organization=self.organization, user=self.user_2, role=self.org_view_role
    #     )

    #     # set db connection to organization schema
    #     connection.set_schema(self.organization.schema_name)

    #     # create video in the org workspace
    #     video_org = Video.objects.create(
    #         title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
    #     )

    #     # create plio within the org workspace by user 2
    #     plio_org = Plio.objects.create(
    #         name="Plio 1", video=video_org, created_by=self.user_2
    #     )

    #     # set organization in request
    #     self.client.credentials(
    #         HTTP_ORGANIZATION=self.organization.shortcode,
    #         HTTP_AUTHORIZATION="Bearer " + self.access_token.token,
    #     )

    #     # get plios
    #     response = self.client.get(reverse("plios-list"))

    #     # the plio created above should be listed
    #     self.assertEqual(len(response.data["results"]), 1)
    #     self.assertEqual(response.data["results"][0]["uuid"], plio_org.uuid)

    #     # reset the connection
    #     connection.set_schema("public")

    def test_guest_cannot_list_plio_uuids(self):
        # unset the credentials
        self.client.credentials()
        # get plio uuids
        response = self.client.get("/api/v1/plios/list_uuid/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list_empty_plio_uuids(self):
        """Test valid user listing plio uuids when they have no plios"""
        # change user
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + self.access_token_2.token
        )
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

    def test_guest_cannot_play_plio(self):
        # unset the credentials
        self.client.credentials()
        # play plio
        response = self.client.get(f"/api/v1/plios/{self.plio_1.uuid}/play/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_play_own_plio(self):
        # play plio
        response = self.client.get(f"/api/v1/plios/{self.plio_1.uuid}/play/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_can_play_other_public_plio(self):
        """Test that an authenticated user can play public plios created by others"""
        # change user
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + self.access_token_2.token
        )
        # play plio
        response = self.client.get(f"/api/v1/plios/{self.plio_1.uuid}/play/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_cannot_play_other_private_plio(self):
        """Test that an authenticated user cannot play private plios created by others"""
        # create a private plio
        private_plio = Plio.objects.create(
            name="Plio Private", video=self.video, created_by=self.user, is_public=False
        )
        # change user
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + self.access_token_2.token
        )
        # play plio
        response = self.client.get(f"/api/v1/plios/{private_plio.uuid}/play/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_play_own_private_plio(self):
        """Test that an authenticated user can play their own private plios"""
        # create a private plio
        private_plio = Plio.objects.create(
            name="Plio Private", video=self.video, created_by=self.user, is_public=False
        )
        # play plio
        response = self.client.get(f"/api/v1/plios/{private_plio.uuid}/play/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_can_duplicate_their_plio(self):
        plio = Plio.objects.filter(created_by=self.user).first()
        # duplicate plio
        response = self.client.post(f"/api/v1/plios/{plio.uuid}/duplicate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertNotEqual(plio.id, response.data["id"])
        self.assertNotEqual(plio.uuid, response.data["uuid"])
        self.assertEqual(plio.name, response.data["name"])

    # should not be able to update other's plio
    # should not be able to update other's plio in org


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

        # seed a video
        self.video = Video.objects.create(
            title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )
        # seed a plio
        self.plio = Plio.objects.create(
            name="Plio", video=self.video, created_by=self.user
        )
        # seed an item
        self.item = Item.objects.create(type="question", plio=self.plio, time=1)

    def test_guest_cannot_list_items(self):
        # unset the credentials
        self.client.credentials()
        # get items
        response = self.client.get(reverse("items-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_list_items(self):
        # get items
        response = self.client.get(reverse("items-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_user_list_own_items(self):
        """A user should only be able to list their own items"""
        # create plio from a different user
        new_plio = Plio.objects.create(
            name="Plio 2", video=self.video, created_by=self.user_2
        )

        # create item from a different user
        Item.objects.create(type="question", plio=new_plio, time=1)

        # get items
        response = self.client.get(reverse("items-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # the count should remain 1 as the new item was created with different user
        self.assertEqual(len(response.data), 1)

    def test_duplicate_no_plio_id(self):
        """Testing duplicate without providing any plio id"""
        # duplicate item
        response = self.client.post(f"/api/v1/items/{self.item.id}/duplicate/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_duplicate_wrong_plio_id(self):
        """Testing duplicate by providing plio id that does not exist"""
        # duplicate item
        response = self.client.post(
            f"/api/v1/items/{self.item.id}/duplicate/", {"plioId": 2}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            json.loads(response.content)["detail"], "Specified plio not found"
        )

    def test_user_can_duplicate_own_item(self):
        """User should be able to duplicate an item previously created by the user"""
        # duplicate item
        response = self.client.post(
            f"/api/v1/items/{self.item.id}/duplicate/", {"plioId": self.plio.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertNotEqual(self.item.id, response.data["id"])
        self.assertEqual(self.item.type, response.data["type"])
        self.assertEqual(self.item.time, response.data["time"])

    # should not be able to update other plio with own item
    # should not be able to update other item

    # def test_user_list_own_plios_in_org(self):
    #     """A user should be able to list their own plios in org workspace"""
    #     # add user to organization
    #     OrganizationUser.objects.create(
    #         organization=self.organization, user=self.user, role=self.org_view_role
    #     )

    #     # set db connection to organization schema
    #     connection.set_schema(self.organization.schema_name)

    #     # create video in the org workspace
    #     video_org = Video.objects.create(
    #         title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
    #     )

    #     # create plio within the org workspace
    #     plio_org = Plio.objects.create(
    #         name="Plio 1", video=video_org, created_by=self.user
    #     )

    #     # set organization in request
    #     self.client.credentials(
    #         HTTP_ORGANIZATION=self.organization.shortcode,
    #         HTTP_AUTHORIZATION="Bearer " + self.access_token.token,
    #     )

    #     # get plios
    #     response = self.client.get(reverse("plios-list"))

    #     # the plio created above should be listed
    #     self.assertEqual(len(response.data["results"]), 1)
    #     self.assertEqual(response.data["results"][0]["uuid"], plio_org.uuid)

    #     # reset the connection
    #     connection.set_schema("public")

    # def test_user_list_other_plios_in_org(self):
    #     """A user should be able to list plios created by others in org workspace"""
    #     # add users to organization
    #     OrganizationUser.objects.create(
    #         organization=self.organization, user=self.user, role=self.org_view_role
    #     )

    #     OrganizationUser.objects.create(
    #         organization=self.organization, user=self.user_2, role=self.org_view_role
    #     )

    #     # set db connection to organization schema
    #     connection.set_schema(self.organization.schema_name)

    #     # create video in the org workspace
    #     video_org = Video.objects.create(
    #         title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
    #     )

    #     # create plio within the org workspace by user 2
    #     plio_org = Plio.objects.create(
    #         name="Plio 1", video=video_org, created_by=self.user_2
    #     )

    #     # set organization in request
    #     self.client.credentials(
    #         HTTP_ORGANIZATION=self.organization.shortcode,
    #         HTTP_AUTHORIZATION="Bearer " + self.access_token.token,
    #     )

    #     # get plios
    #     response = self.client.get(reverse("plios-list"))

    #     # the plio created above should be listed
    #     self.assertEqual(len(response.data["results"]), 1)
    #     self.assertEqual(response.data["results"][0]["uuid"], plio_org.uuid)

    #     # reset the connection
    #     connection.set_schema("public")


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

        # upload a test image and retrieve the id
        with open("plio/static/plio/test_image.jpeg", "rb") as img:
            response = self.client.post(
                reverse("images-list"), {"url": img, "alt_text": "test image"}
            )
        self.image = response.json()["id"]

    def test_user_can_upload_image(self):
        """
        Tests whether an authorized user can create/upload an image
        """
        with open("plio/static/plio/test_image.jpeg", "rb") as img:
            response = self.client.post(reverse("images-list"), {"url": img})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_can_attach_images_to_their_question(self):
        """
        Tests whether a user can link images to the questions
        that were created by themselves
        """
        # update the question with the newly uploaded image
        response = self.client.put(
            reverse("questions-detail", args=[self.test_question.id]),
            {"item": self.test_item.id, "image": self.image},
        )
        # the user should be able to update the question
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_cannot_attach_image_to_other_user_question(self):
        """
        Tests that a user should NOT be able to link images to
        the questions that were created by some other user
        """
        # reset the credentials to that of another user
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + self.access_token_2.token
        )

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

    # def test_user_can_duplicate_image(self):
    #     """Tests the duplicate functionality for images"""
    #     # duplicate image
    #     response = self.client.post(f"/api/v1/images/{self.image.id}/duplicate/")
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    #     self.assertNotEqual(self.item.id, response.data["id"])
    #     self.assertEqual(self.item.type, response.data["type"])
    #     self.assertEqual(self.item.time, response.data["time"])

    # should only be able to view own images
    # should only be able to update own images
    # appropriate tests for org
