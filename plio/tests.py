import datetime
import random
import string
import json
from django.utils import timezone
from django.http import FileResponse

from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from rest_framework import status
from oauth2_provider.models import Application
from oauth2_provider.models import AccessToken
from django.urls import reverse
from django.db import connection

from users.models import User, Role, OrganizationUser
from organizations.models import Organization
from plio.settings import API_APPLICATION_NAME, OAUTH2_PROVIDER
from plio.models import Plio, Video, Item, Question, Image
from entries.models import Session
from plio.views import StandardResultsSetPagination


class BaseTestCase(APITestCase):
    """Base class that sets up generic pre-requisites for all further test classes"""

    @classmethod
    def setUpTestData(self):
        self.client = APIClient()

        # User access and refresh tokens require an OAuth Provider application to be set up and use it as a foreign key.
        # As the test database is empty, we create an application instance before running the test cases.
        self.application = Application.objects.create(
            name=API_APPLICATION_NAME,
            redirect_uris="",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )

        # create org
        self.organization = Organization.objects.create(name="Org 1", shortcode="org-1")

        # get roles
        self.org_view_role = Role.objects.filter(name="org-view").first()
        self.org_admin_role = Role.objects.filter(name="org-admin").first()
        self.super_admin_role = Role.objects.filter(name="super-admin").first()

    def setUp(self):
        # create 2 users
        self.user = User.objects.create(mobile="+919876543210")
        self.user_2 = User.objects.create(mobile="+919988776655")

        # set up access token for the user
        self.access_token = get_new_access_token(self.user, self.application)
        self.access_token_2 = get_new_access_token(self.user_2, self.application)

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
        # create plio from user 2
        Plio.objects.create(name="Plio 1", video=self.video, created_by=self.user_2)

        # get plios
        response = self.client.get(reverse("plios-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # the count should remain 2 as the new plio was created with user 2
        self.assertEqual(response.data["count"], 2)

    def test_user_list_own_plios_in_org(self):
        """A user should be able to list their own plios in org workspace"""
        # add user to organization
        OrganizationUser.objects.create(
            organization=self.organization, user=self.user, role=self.org_view_role
        )

        # set db connection to organization schema
        connection.set_schema(self.organization.schema_name)

        # create video in the org workspace
        video_org = Video.objects.create(
            title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )

        # create plio within the org workspace
        plio_org = Plio.objects.create(
            name="Plio 1", video=video_org, created_by=self.user
        )

        # set organization in request
        self.client.credentials(
            HTTP_ORGANIZATION=self.organization.shortcode,
            HTTP_AUTHORIZATION="Bearer " + self.access_token.token,
        )

        # get plios
        response = self.client.get(reverse("plios-list"))

        # the plio created above should be listed
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["uuid"], plio_org.uuid)

        # set db connection back to public (default) schema
        connection.set_schema_to_public()

    def test_user_list_other_plios_in_org(self):
        """A user should be able to list plios created by others in org workspace"""
        # add users to organization
        OrganizationUser.objects.create(
            organization=self.organization, user=self.user, role=self.org_view_role
        )

        OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.org_view_role
        )

        # set db connection to organization schema
        connection.set_schema(self.organization.schema_name)

        # create video in the org workspace
        video_org = Video.objects.create(
            title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )

        # create plio within the org workspace by user 2
        plio_org = Plio.objects.create(
            name="Plio 1", video=video_org, created_by=self.user_2
        )

        # set organization in request and access token for user 1
        self.client.credentials(
            HTTP_ORGANIZATION=self.organization.shortcode,
            HTTP_AUTHORIZATION="Bearer " + self.access_token.token,
        )

        # get plios
        response = self.client.get(reverse("plios-list"))

        # the plio created above should be listed
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["uuid"], plio_org.uuid)

        # set db connection back to public (default) schema
        connection.set_schema_to_public()

    def test_guest_cannot_list_plio_uuids(self):
        # unset the credentials
        self.client.credentials()
        # get plio uuids
        response = self.client.get("/api/v1/plios/list_uuid/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list_empty_plio_uuids(self):
        """Tests that a user with no plios receives an empty list of uuids"""
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
                "page_size": StandardResultsSetPagination.page_size,
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
                "page_size": StandardResultsSetPagination.page_size,
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
        # play plio created by user 1
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

    def test_duplicate(self):
        plio = Plio.objects.filter(created_by=self.user).first()
        # duplicate plio
        response = self.client.post(f"/api/v1/plios/{plio.uuid}/duplicate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertNotEqual(plio.id, response.data["id"])
        self.assertNotEqual(plio.uuid, response.data["uuid"])
        self.assertEqual(plio.name, response.data["name"])

    def test_default_ordering_when_no_ordering_specified(self):
        # create a third plio
        Plio.objects.create(name="Plio 3", video=self.video, created_by=self.user)

        # make a request to list the plio uuids without specifying any order
        # NOTE: default ordering should come out to be '-updated_at'
        # order of plios should be [plio_3, plio_2, plio_1]
        response = self.client.get("/api/v1/plios/list_uuid/")
        self.assertListEqual(
            [plio.uuid for plio in Plio.objects.order_by("-updated_at")],
            response.data["results"],
        )

        # update the first plio - ordering should change according to 'updated_at'
        self.plio_1.name = "updated Plio 1"
        self.plio_1.save()

        # make a request to list the plio uuids
        # NOTE: default ordering should come out to be '-updated_at'
        # order of plios should be [plio_1, plio_3, plio_2]
        response = self.client.get("/api/v1/plios/list_uuid/")
        self.assertListEqual(
            [plio.uuid for plio in Plio.objects.order_by("-updated_at")],
            response.data["results"],
        )

    def test_ordering_applied_as_specified(self):
        # create a third plio
        plio_3 = Plio.objects.create(
            name="Plio 3", video=self.video, created_by=self.user
        )

        # ordering by "name"
        # update the names
        self.plio_1.name = "A_plio"
        self.plio_1.save()
        self.plio_2.name = "B_plio"
        self.plio_2.save()
        plio_3.name = "C_plio"
        plio_3.save()

        # `list_uuid` should give the result ordered as [plio_1, plio_2, plio_3]
        # when "name" ordering is specified
        response = self.client.get("/api/v1/plios/list_uuid/", {"ordering": "name"})
        self.assertListEqual(
            [plio.uuid for plio in Plio.objects.order_by("name")],
            response.data["results"],
        )

        # ordering by "-name"
        # 'list_uuid` should give the result ordered as [plio_3, plio_2, plio_1]
        # when "-name" ordering is specified
        response = self.client.get("/api/v1/plios/list_uuid/", {"ordering": "-name"})
        self.assertListEqual(
            [plio.uuid for plio in Plio.objects.order_by("-name")],
            response.data["results"],
        )

        # ordering by 'created_at'
        # 'list_uuid` should give the result ordered as [plio_1, plio_2, plio_3]
        # when "created_at" ordering is specified
        response = self.client.get(
            "/api/v1/plios/list_uuid/", {"ordering": "created_at"}
        )
        self.assertListEqual(
            [plio.uuid for plio in Plio.objects.order_by("created_at")],
            response.data["results"],
        )

        # ordering by "-unique_viewers"
        # stimulate some users watching the created plios
        user_3 = User.objects.create(mobile="+918877665544")

        # seed sessions such that the three plios have this decending
        # configuration of number of unique viewers
        # plio_3 - 3 | plio_2 - 2 | plio_1 - 2
        Session.objects.create(plio=plio_3, user=user_3)
        Session.objects.create(plio=plio_3, user=self.user_2)
        Session.objects.create(plio=plio_3, user=self.user)

        Session.objects.create(plio=self.plio_2, user=self.user_2)
        Session.objects.create(plio=self.plio_2, user=self.user)

        Session.objects.create(plio=self.plio_1, user=self.user_2)
        Session.objects.create(plio=self.plio_1, user=self.user)

        # 'list_uuid` should give the result ordered as [plio_3, plio_2, plio_1]
        # when "-unique_viewers" ordering is specified
        response = self.client.get(
            "/api/v1/plios/list_uuid/", {"ordering": "-unique_viewers"}
        )
        self.assertListEqual(
            [plio_3.uuid, self.plio_2.uuid, self.plio_1.uuid], response.data["results"]
        )

        # ordering by "-unique_viewers" and "name"
        # 'list_uuid` should give the result ordered as [plio_3, plio_1, plio_2]
        # when ordering is specified as "-unique_viewers" and "name"
        response = self.client.get(
            "/api/v1/plios/list_uuid/", {"ordering": "-unique_viewers,name"}
        )
        self.assertListEqual(
            [plio_3.uuid, self.plio_1.uuid, self.plio_2.uuid], response.data["results"]
        )

    def test_invalid_ordering_results_in_default_ordering(self):
        # create a third plio
        Plio.objects.create(name="Plio 3", video=self.video, created_by=self.user)

        # order by some invalid ordering string - "xyz"
        # `list_uuid` should give the result ordered as [plio_3, plio_2, plio_1]
        # because an invalid ordering field will result in the default ordering
        response = self.client.get("/api/v1/plios/list_uuid/", {"ordering": "xyz"})
        self.assertListEqual(
            [plio.uuid for plio in Plio.objects.order_by("-updated_at")],
            response.data["results"],
        )


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

    def test_user_list_items_by_plio(self):
        # create a new plio
        new_plio = Plio.objects.create(
            name="Plio 2", video=self.video, created_by=self.user
        )
        # attach a new item to the new plio
        Item.objects.create(type="question", plio=new_plio, time=1)

        # get items
        response = self.client.get(reverse("items-list"), {"plio": self.plio.uuid})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # the number of responses should still be 1 - the item created above
        # should not be included
        self.assertEqual(len(response.data), 1)

    def test_user_list_other_user_items(self):
        """A user should be able to list items created by others too"""
        # create a plio from user 2
        new_plio = Plio.objects.create(
            name="Plio 2", video=self.video, created_by=self.user_2
        )

        # create an item from user 2
        Item.objects.create(type="question", plio=new_plio, time=1)

        # get items
        response = self.client.get(reverse("items-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # user should be able to list all items
        self.assertEqual(len(response.data), 2)

    def test_org_user_can_list_own_items(self):
        # add user to organization
        OrganizationUser.objects.create(
            organization=self.organization, user=self.user, role=self.org_view_role
        )

        # set db connection to organization schema
        connection.set_schema(self.organization.schema_name)

        # create video in the org workspace
        video_org = Video.objects.create(
            title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )

        # create plio within the org workspace
        plio_org = Plio.objects.create(
            name="Plio 1", video=video_org, created_by=self.user
        )

        item_org = Item.objects.create(type="question", plio=plio_org, time=1)

        # set organization in request
        self.client.credentials(
            HTTP_ORGANIZATION=self.organization.shortcode,
            HTTP_AUTHORIZATION="Bearer " + self.access_token.token,
        )

        # get items
        response = self.client.get(reverse("items-list"))

        # the item created above should be listed
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], item_org.id)

        # set db connection back to public (default) schema
        connection.set_schema_to_public()

    def test_org_user_can_list_other_user_items(self):
        # add users to organization
        OrganizationUser.objects.create(
            organization=self.organization, user=self.user, role=self.org_view_role
        )

        OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.org_view_role
        )

        # set db connection to organization schema
        connection.set_schema(self.organization.schema_name)

        # create video in the org workspace
        video_org = Video.objects.create(
            title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )

        # create plio within the org workspace
        plio_org = Plio.objects.create(
            name="Plio 1", video=video_org, created_by=self.user_2
        )

        item_org = Item.objects.create(type="question", plio=plio_org, time=1)

        # set organization in request
        self.client.credentials(
            HTTP_ORGANIZATION=self.organization.shortcode,
            HTTP_AUTHORIZATION="Bearer " + self.access_token.token,
        )

        # get plios
        response = self.client.get(reverse("items-list"))

        # the plio created above should be listed
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], item_org.id)

        # set db connection back to public (default) schema
        connection.set_schema_to_public()

    def test_guest_cannot_update_items(self):
        # unset the credentials
        self.client.credentials()
        # update item
        response = self.client.put(
            f"/api/v1/items/{self.item.id}/", {"time": 2, "plio": self.plio.id}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_update_own_items(self):
        # update item
        response = self.client.put(
            f"/api/v1/items/{self.item.id}/", {"time": 2, "plio": self.plio.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check item was updated
        response = self.client.get(f"/api/v1/items/{self.item.id}/")
        self.assertEqual(response.json()["time"], 2)

    def test_user_cannot_update_other_items(self):
        # create a plio from user 2
        new_plio = Plio.objects.create(
            name="Plio 2", video=self.video, created_by=self.user_2
        )

        # create an item from user 2
        new_item = Item.objects.create(type="question", plio=new_plio, time=1)

        # update item
        response = self.client.put(
            f"/api/v1/items/{new_item.id}/", {"time": 2, "plio": self.plio.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_update_all_items(self):
        # make self.user superuser
        self.user.is_superuser = True
        self.user.save()

        # create a plio from user 2
        new_plio = Plio.objects.create(
            name="Plio 2", video=self.video, created_by=self.user_2
        )

        # create an item from user 2
        new_item = Item.objects.create(type="question", plio=new_plio, time=1)

        # test that self.user (superuser) can update item created by user 2
        response = self.client.put(
            f"/api/v1/items/{new_item.id}/", {"time": 2, "plio": new_plio.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check item was updated
        response = self.client.get(f"/api/v1/items/{new_item.id}/")
        self.assertEqual(response.json()["time"], 2)

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

    def test_duplicate(self):
        """Tests the duplicate functionality"""
        # duplicate item
        response = self.client.post(
            f"/api/v1/items/{self.item.id}/duplicate/", {"plioId": self.plio.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertNotEqual(self.item.id, response.data["id"])
        self.assertEqual(self.item.type, response.data["type"])
        self.assertEqual(self.item.time, response.data["time"])


class QuestionTestCase(BaseTestCase):
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

        # seed a question
        self.question = Question.objects.create(type="mcq", item=self.item, text="test")

    def test_guest_cannot_update_questions(self):
        # unset the credentials
        self.client.credentials()
        # update question
        response = self.client.put(
            f"/api/v1/questions/{self.question.id}/",
            {"type": "subjective", "item": self.item.id},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_update_own_questions(self):
        # update question
        response = self.client.put(
            f"/api/v1/questions/{self.question.id}/",
            {"type": "subjective", "item": self.item.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check question was updated
        response = self.client.get(f"/api/v1/questions/{self.question.id}/")
        self.assertEqual(response.json()["type"], "subjective")

    def test_user_cannot_update_other_user_questions(self):
        # create a plio from user 2
        new_plio = Plio.objects.create(
            name="Plio 2", video=self.video, created_by=self.user_2
        )

        # create an item from user 2
        new_item = Item.objects.create(type="question", plio=new_plio, time=1)

        # create a question from user 2
        new_question = Question.objects.create(type="mcq", item=new_item, text="test-2")

        # update question
        response = self.client.put(
            f"/api/v1/questions/{new_question.id}/",
            {"type": "subjective", "item": self.item.id},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_update_all_questions(self):
        # make self.user superuser
        self.user.is_superuser = True
        self.user.save()

        # create a plio from user 2
        new_plio = Plio.objects.create(
            name="Plio 2", video=self.video, created_by=self.user_2
        )

        # create an item from user 2
        new_item = Item.objects.create(type="question", plio=new_plio, time=1)

        # create a question from user 2
        new_question = Question.objects.create(type="mcq", item=new_item, text="test-2")

        # test that self.user can update question created by user 2
        response = self.client.put(
            f"/api/v1/questions/{new_question.id}/",
            {"type": "subjective", "item": self.item.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check question was updated
        response = self.client.get(f"/api/v1/questions/{new_question.id}/")
        self.assertEqual(response.json()["type"], "subjective")

    def test_duplicate_no_item_id(self):
        """Testing duplicate without providing any item id"""
        # duplicate question
        response = self.client.post(f"/api/v1/questions/{self.question.id}/duplicate/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_duplicate_wrong_item_id(self):
        """Testing duplicate by providing item id that does not exist"""
        # duplicate question
        response = self.client.post(
            f"/api/v1/questions/{self.question.id}/duplicate/",
            {"itemId": self.item.id + 100},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            json.loads(response.content)["detail"], "Specified item not found"
        )

    def test_duplicate_own_question(self):
        """Tests the duplicate functionality"""
        # duplicate question
        response = self.client.post(
            f"/api/v1/questions/{self.question.id}/duplicate/", {"itemId": self.item.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertNotEqual(self.question.id, response.data["id"])
        self.assertEqual(self.question.type, response.data["type"])
        self.assertEqual(self.question.text, response.data["text"])

    def test_duplicate_question_with_image(self):
        """Tests the duplicate functionality for a question which has an image"""
        # upload a test image and retrieve the id
        with open("plio/static/plio/test_image.jpeg", "rb") as img:
            response = self.client.post(
                reverse("images-list"), {"url": img, "alt_text": "test image"}
            )
        image_id = response.json()["id"]

        # attach image id to question
        response = self.client.put(
            reverse("questions-detail", args=[self.question.id]),
            {"item": self.item.id, "image": image_id},
        )

        # duplicate question
        response = self.client.post(
            f"/api/v1/questions/{self.question.id}/duplicate/", {"itemId": self.item.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertNotEqual(self.question.id, response.data["id"])
        self.assertEqual(self.question.type, response.data["type"])
        self.assertEqual(self.question.text, response.data["text"])
        self.assertIsNotNone(response.data["image"])
        self.assertNotEqual(self.question.image, response.data["image"])


class ImageTestCase(BaseTestCase):
    """Tests the Image CRUD functionality."""

    def setUp(self):
        super().setUp()
        # seed a video
        self.video = Video.objects.create(
            title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )
        # seed a plio, item and question
        self.plio = Plio.objects.create(
            name="test_plio", video=self.video, created_by=self.user
        )
        self.item = Item.objects.create(plio=self.plio, type="question", time=1)
        self.question = Question.objects.create(item=self.item)

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
            reverse("questions-detail", args=[self.question.id]),
            {"item": self.item.id, "image": self.image},
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
            reverse("questions-detail", args=[self.question.id]),
            {"item": self.item.id, "image": uploaded_image_id},
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

    def test_duplicate_image(self):
        """Tests the duplicate functionality for images"""
        # duplicate image
        response = self.client.post(f"/api/v1/images/{self.image}/duplicate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        image = Image.objects.filter(id=self.image).first()
        new_image = Image.objects.filter(id=response.data["id"]).first()

        self.assertNotEqual(self.image, response.data["id"])
        self.assertEqual(image.alt_text, response.data["alt_text"])
        self.assertEqual(image.url.file.size, new_image.url.file.size)


class PlioDownloadTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        # seed a video
        self.video = Video.objects.create(
            title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )
        # seed a plio
        self.plio = Plio.objects.create(
            name="Plio 1", video=self.video, created_by=self.user, status="published"
        )
        # seed some sessions for the plio
        Session.objects.create(plio=self.plio, user=self.user)
        Session.objects.create(plio=self.plio, user=self.user)

    def test_draft_plio_data_cannot_be_downloaded(self):
        # change plio status to draft
        self.plio.status = "draft"
        self.plio.save()
        # download plio data
        response = self.client.get(f"/api/v1/plios/{self.plio.uuid}/download_data/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_published_plio_data_can_be_downloaded(self):
        # download plio data
        response = self.client.get(f"/api/v1/plios/{self.plio.uuid}/download_data/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response, FileResponse))

    def test_non_plio_owner_cannot_download_data(self):
        # make a plio with new user
        new_user_plio = Plio.objects.create(
            name="Plio 2", video=self.video, created_by=self.user_2, status="published"
        )
        # download new user plio data
        response = self.client.get(f"/api/v1/plios/{new_user_plio.uuid}/download_data/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_download_data_for_other_user_plio_in_organization(self):

        OrganizationUser.objects.create(
            organization=self.organization, user=self.user, role=self.org_view_role
        )
        OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.org_view_role
        )

        # set db connection to organization schema
        connection.set_schema(self.organization.schema_name)

        # create a video within the organization schema
        new_user_video = Video.objects.create(
            title="Video 2", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )
        # create a plio with new user inside the organization schema
        new_user_plio = Plio.objects.create(
            name="Plio 2",
            video=new_user_video,
            created_by=self.user_2,
            status="published",
        )

        # add the organization shortcode in the request header and download new user plio data
        response = self.client.get(
            f"/api/v1/plios/{new_user_plio.uuid}/download_data/",
            HTTP_ORGANIZATION=self.organization.shortcode,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response, FileResponse))

        # set db connection back to public (default) schema
        connection.set_schema_to_public()
