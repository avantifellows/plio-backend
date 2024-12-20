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
from django.core.cache import cache
from django_redis import get_redis_connection

from users.models import User, Role, OrganizationUser
from organizations.models import Organization
from plio.settings import API_APPLICATION_NAME, OAUTH2_PROVIDER
from plio.models import Plio, Video, Item, Question, Image
from entries.models import Session, SessionAnswer
from plio.views import StandardResultsSetPagination
from plio.cache import get_cache_key
from plio.serializers import ImageSerializer


def get_uuid_list(plio_list):
    return [plio["uuid"] for plio in plio_list]


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

    def tearDown(self):
        # flush the cache
        get_redis_connection("default").flushall()

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
        response = self.client.get("/api/v1/plios/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_list_plios(self):
        # get plios
        response = self.client.get("/api/v1/plios/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_user_list_own_plios(self):
        """A user should only be able to list their own plios"""
        # create plio from user 2
        Plio.objects.create(name="Plio 1", video=self.video, created_by=self.user_2)

        # get plios
        response = self.client.get("/api/v1/plios/")
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
        response = self.client.get("/api/v1/plios/")

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
        response = self.client.get("/api/v1/plios/")

        # the plio created above should be listed
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["uuid"], plio_org.uuid)

        # set db connection back to public (default) schema
        connection.set_schema_to_public()

    def test_non_org_user_cannot_list_plios_in_org(self):
        """A user who is not in an org should not be able to list plios in org workspace"""
        # set db connection to organization schema
        connection.set_schema(self.organization.schema_name)

        # create video in the org workspace
        video_org = Video.objects.create(
            title="Video 1", url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )

        # create plio within the org workspace by user 1
        Plio.objects.create(name="Plio 1", video=video_org, created_by=self.user)

        # set organization in request and access token for user 2
        self.client.credentials(
            HTTP_ORGANIZATION=self.organization.shortcode,
            HTTP_AUTHORIZATION="Bearer " + self.access_token_2.token,
        )

        # get plios
        response = self.client.get("/api/v1/plios/")

        # no plios should be listed
        self.assertEqual(len(response.data["results"]), 0)

        # set db connection back to public (default) schema
        connection.set_schema_to_public()

    def test_guest_cannot_list_plio_uuids(self):
        # unset the credentials
        self.client.credentials()
        response = self.client.get("/api/v1/plios/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list_empty_plio(self):
        """Tests that a user with no plios receives an empty list of uuids"""
        # change user
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + self.access_token_2.token
        )
        response = self.client.get("/api/v1/plios/")
        self.assertEqual(
            response.data,
            {
                "count": 0,
                "page_size": StandardResultsSetPagination.page_size,
                "next": None,
                "previous": None,
                "results": [],
                "raw_count": 0,
            },
        )

    def test_user_list_with_plios(self):
        """Test valid user listing plio uuids when they have plios"""
        response = self.client.get("/api/v1/plios/")

        expected_results = list(
            Plio.objects.filter(id__in=[self.plio_2.id, self.plio_1.id]).values()
        )

        for index, _ in enumerate(expected_results):
            expected_results[index]["unique_viewers"] = 0
            expected_results[index]["video_url"] = self.video.url

        self.assertEqual(
            response.data,
            {
                "count": 2,
                "page_size": StandardResultsSetPagination.page_size,
                "next": None,
                "previous": None,
                "results": expected_results,
                "raw_count": 2,
            },
        )

    def test_listing_plios_returns_unique_num_views(self):
        # create some sessions - 2 sessions for one user and one more session for another user
        Session.objects.create(plio=self.plio_1, user=self.user)
        Session.objects.create(plio=self.plio_1, user=self.user)
        Session.objects.create(plio=self.plio_1, user=self.user_2)

        response = self.client.get("/api/v1/plios/")
        plios = response.data["results"]

        # plio 2 will be listed first because it was created later
        expected_num_unique_viewers = [0, 2]
        self.assertEqual(
            [plio["unique_viewers"] for plio in plios], expected_num_unique_viewers
        )

    def test_guest_can_play_plio(self):
        # unset the credentials
        self.client.credentials()
        # play plio
        response = self.client.get(f"/api/v1/plios/{self.plio_1.uuid}/play/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

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
        # create some items and questions
        item_1 = Item.objects.create(type="question", plio=self.plio_1, time=1)
        item_2 = Item.objects.create(type="question", plio=self.plio_1, time=10)
        item_3 = Item.objects.create(type="question", plio=self.plio_1, time=20)

        question_1 = Question.objects.create(type="checkbox", item=item_1)
        # attach an image to one question
        # upload a test image and retrieve the id
        with open("plio/static/plio/test_image.jpeg", "rb") as img:
            response = self.client.post(
                "/api/v1/images/", {"url": img, "alt_text": "test image"}
            )
        image_id = response.json()["id"]
        question_2 = Question.objects.create(
            type="subjective",
            item=item_2,
            image=Image.objects.filter(id=image_id).first(),
        )
        question_3 = Question.objects.create(type="checkbox", item=item_3)
        response = self.client.post(
            f"/api/v1/plios/{self.plio_1.uuid}/duplicate/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_plio_id = response.data["id"]
        new_plio_uuid = response.data["uuid"]
        new_video_id = response.data["video"]["id"]
        new_item_ids = []
        new_question_ids = []

        for item in response.data.get("items", []):
            new_item_ids.append(item["id"])
            new_question_ids.append(item["details"]["id"])

        response = self.client.get(
            f"/api/v1/videos/{new_video_id}/",
        )
        self.assertNotEqual(new_video_id, self.video.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(
            f"/api/v1/plios/{new_plio_uuid}/",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for new_item_id, old_item in zip(new_item_ids, [item_1, item_2, item_3]):
            response = self.client.get(
                f"/api/v1/items/{new_item_id}/",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["plio"], new_plio_id)
            self.assertEqual(response.data["type"], old_item.type)
            self.assertEqual(response.data["time"], old_item.time)

        for old_question, new_question_id, new_item_id in zip(
            [question_1, question_2, question_3],
            new_question_ids,
            new_item_ids,
        ):
            response = self.client.get(
                f"/api/v1/questions/{new_question_id}/",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["item"], new_item_id)
            self.assertEqual(response.data["type"], old_question.type)

            if old_question.image is not None:
                self.assertEqual(
                    ImageSerializer(old_question.image).data["url"],
                    response.data["image"]["url"],
                )

    def test_default_ordering_when_no_ordering_specified(self):
        # create a third plio
        plio_3 = Plio.objects.create(
            name="Plio 3", video=self.video, created_by=self.user
        )

        # make a request to list the plio uuids without specifying any order
        # NOTE: default ordering should come out to be '-updated_at'
        # order of plios should be [plio_3, plio_2, plio_1]
        response = self.client.get("/api/v1/plios/")
        results = get_uuid_list(response.data["results"])
        self.assertListEqual(
            [plio.uuid for plio in Plio.objects.order_by("-updated_at")],
            results,
        )
        # also manually checking the order
        self.assertListEqual(
            [plio_3.uuid, self.plio_2.uuid, self.plio_1.uuid],
            results,
        )

        # update the first plio - ordering should change according to 'updated_at'
        self.plio_1.name = "updated Plio 1"
        self.plio_1.save()

        # make a request to list the plio uuids
        # NOTE: default ordering should come out to be '-updated_at'
        # order of plios should be [plio_1, plio_3, plio_2]
        response = self.client.get("/api/v1/plios/")
        results = get_uuid_list(response.data["results"])
        self.assertListEqual(
            [plio.uuid for plio in Plio.objects.order_by("-updated_at")],
            results,
        )
        # also manually checking the order
        self.assertListEqual(
            [self.plio_1.uuid, plio_3.uuid, self.plio_2.uuid],
            results,
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

        # listing plios should give the result ordered as [plio_1, plio_2, plio_3]
        # when "name" ordering is specified
        response = self.client.get("/api/v1/plios/", {"ordering": "name"})
        results = get_uuid_list(response.data["results"])
        self.assertListEqual(
            [plio.uuid for plio in Plio.objects.order_by("name")],
            results,
        )
        # also manually checking the order
        self.assertListEqual(
            [self.plio_1.uuid, self.plio_2.uuid, plio_3.uuid],
            results,
        )

        # ordering by "-name"
        # listing plios should give the result ordered as [plio_3, plio_2, plio_1]
        # when "-name" ordering is specified
        response = self.client.get("/api/v1/plios/", {"ordering": "-name"})
        results = get_uuid_list(response.data["results"])
        self.assertListEqual(
            [plio.uuid for plio in Plio.objects.order_by("-name")],
            results,
        )
        # also manually checking the order
        self.assertListEqual(
            [plio_3.uuid, self.plio_2.uuid, self.plio_1.uuid],
            results,
        )

        # ordering by 'created_at'
        # listing plios should give the result ordered as [plio_1, plio_2, plio_3]
        # when "created_at" ordering is specified
        response = self.client.get("/api/v1/plios/", {"ordering": "created_at"})
        results = get_uuid_list(response.data["results"])
        self.assertListEqual(
            [plio.uuid for plio in Plio.objects.order_by("created_at")],
            results,
        )
        # also manually checking the order
        self.assertListEqual(
            [self.plio_1.uuid, self.plio_2.uuid, plio_3.uuid],
            results,
        )

        # ordering by "-unique_viewers"
        # stimulate some users watching the created plios
        user_3 = User.objects.create(mobile="+918877665544")

        # seed sessions such that the three plios have this decending
        # configuration of number of unique viewers
        # plio_3 - 3 | plio_2 - 2 | plio_1 - 1
        Session.objects.create(plio=plio_3, user=user_3)
        Session.objects.create(plio=plio_3, user=self.user_2)
        Session.objects.create(plio=plio_3, user=self.user)

        Session.objects.create(plio=self.plio_2, user=self.user_2)
        Session.objects.create(plio=self.plio_2, user=self.user)

        Session.objects.create(plio=self.plio_1, user=self.user)

        # listing plios should give the result ordered as [plio_3, plio_2, plio_1]
        # when "-unique_viewers" ordering is specified
        response = self.client.get("/api/v1/plios/", {"ordering": "-unique_viewers"})
        self.assertListEqual(
            [plio_3.uuid, self.plio_2.uuid, self.plio_1.uuid],
            get_uuid_list(response.data["results"]),
        )

        # ordering by "-unique_viewers" and "name"
        # listing plios should give the result ordered as [plio_3, plio_1, plio_2]
        # when ordering is specified as "-unique_viewers" and "name"

        # add one more unique_view to plio_1 so that plio_1 and plio_2 both have 2 views each
        # that way, the second ordering will be done using the "name"
        Session.objects.create(plio=self.plio_1, user=self.user_2)
        response = self.client.get(
            "/api/v1/plios/", {"ordering": "-unique_viewers,name"}
        )
        self.assertListEqual(
            [plio_3.uuid, self.plio_1.uuid, self.plio_2.uuid],
            get_uuid_list(response.data["results"]),
        )

    def test_invalid_ordering_results_in_default_ordering(self):
        # create a third plio
        Plio.objects.create(name="Plio 3", video=self.video, created_by=self.user)

        # order by some invalid ordering string - "xyz"
        # listing plios should give the result ordered as [plio_3, plio_2, plio_1]
        # because an invalid ordering field will result in the default ordering
        response = self.client.get("/api/v1/plios/", {"ordering": "xyz"})
        self.assertListEqual(
            [plio.uuid for plio in Plio.objects.order_by("-updated_at")],
            get_uuid_list(response.data["results"]),
        )

    def test_delete(self):
        """Tests the delete functionality"""
        # fetching plio 1 works at first
        response = self.client.get(f"/api/v1/plios/{self.plio_1.uuid}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # delete plio 1
        response = self.client.delete(f"/api/v1/plios/{self.plio_1.uuid}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # fetching plio 1 should now give an error
        response = self.client.get(f"/api/v1/plios/{self.plio_1.uuid}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_items_sorted_with_time(self):
        """Tests that the items returned while getting a plio are sorted by time"""
        # seed an item
        item_1 = Item.objects.create(type="question", plio=self.plio_1, time=10)

        # seed another item with timestamp less than the first item
        item_2 = Item.objects.create(type="question", plio=self.plio_1, time=1)

        # while fetching the plio for the items above, the second item should
        # come before the first item
        response = self.client.get(f"/api/v1/plios/{self.plio_1.uuid}/")
        self.assertEqual(response.data["items"][0]["id"], item_2.id)
        self.assertEqual(response.data["items"][1]["id"], item_1.id)

    def test_retrieving_plio_sets_instance_cache(self):

        # verify cache data doesn't exist
        cache_key_name = get_cache_key(self.plio_1)
        self.assertEqual(len(cache.keys(cache_key_name)), 0)

        # make a get request
        response = self.client.get(
            reverse("plios-detail", kwargs={"uuid": self.plio_1.uuid})
        )

        # verify cache data exists
        self.assertEqual(len(cache.keys(cache_key_name)), 1)
        self.assertEqual(response.data, cache.get(cache_key_name))

    def test_updating_plio_recreates_instance_cache(self):
        # create a third plio
        plio_3 = Plio.objects.create(
            name="Plio 3", video=self.video, created_by=self.user
        )

        # verify cache data doesn't exist
        cache_key_name = get_cache_key(plio_3)
        self.assertEqual(len(cache.keys(cache_key_name)), 0)

        # make a get request
        self.client.get(reverse("plios-detail", kwargs={"uuid": plio_3.uuid}))

        # verify cache data exists
        self.assertEqual(len(cache.keys(cache_key_name)), 1)

        # make an update
        new_name = "Plio name update"
        self.client.patch(
            reverse("plios-detail", kwargs={"uuid": plio_3.uuid}), {"name": new_name}
        )

        # verify cache data exist with the updated value
        self.assertEqual(len(cache.keys(cache_key_name)), 1)
        self.assertEqual(cache.get(cache_key_name)["name"], new_name)

    def test_user_can_update_own_plio_settings(self):
        test_settings = {"player": {"configuration": {"skipEnabled": False}}}

        # update settings for plio_1
        response = self.client.patch(
            f"/api/v1/plios/{self.plio_1.uuid}/setting/",
            test_settings,
            format="json",
        )

        # 200 OK returned as status
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The plio should contain the new updated settings object
        self.assertEqual(
            Plio.objects.filter(uuid=self.plio_1.uuid)
            .first()
            .config["settings"]["player"],
            test_settings["player"],
        )

    def test_user_cannot_update_other_user_plio_settings(self):
        test_settings = {"player": {"configuration": {"skipEnabled": False}}}
        # user_2 creates a plio
        plio = Plio.objects.create(
            name="Plio_by_user_2", video=self.video, created_by=self.user_2
        )

        # user_1 tries updating the settings for the above created plio
        response = self.client.patch(
            f"/api/v1/plios/{plio.uuid}/setting/",
            test_settings,
            format="json",
        )

        # updating other user's plio's settings should be forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_org_members_can_update_org_plio_settings(self):
        test_settings = {"player": {"configuration": {"skipEnabled": False}}}

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

        # user_1 tries to update the org plio's settings which was created
        # by user_2
        response = self.client.patch(
            f"/api/v1/plios/{plio_org.uuid}/setting/",
            test_settings,
            format="json",
        )

        # updating an org plio's settings should be possible by any org member
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Plio.objects.filter(uuid=plio_org.uuid)
            .first()
            .config["settings"]["player"],
            test_settings["player"],
        )

        # set db connection back to public (default) schema
        connection.set_schema_to_public()

    def test_copying_without_specifying_workspace_fails(self):
        response = self.client.post(f"/api/v1/plios/{self.plio_1.uuid}/copy/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "workspace is not provided")

    def test_copying_to_non_existing_workspace_fails(self):
        response = self.client.post(
            f"/api/v1/plios/{self.plio_1.uuid}/copy/", {"workspace": "abcd"}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "workspace does not exist")

    def test_copying_to_workspace(self):
        # create some items and questions
        item_1 = Item.objects.create(type="question", plio=self.plio_1, time=1)
        item_2 = Item.objects.create(type="question", plio=self.plio_1, time=10)
        item_3 = Item.objects.create(type="question", plio=self.plio_1, time=20)

        question_1 = Question.objects.create(type="checkbox", item=item_1)
        # attach an image to one question
        # upload a test image and retrieve the id
        with open("plio/static/plio/test_image.jpeg", "rb") as img:
            response = self.client.post(
                reverse("images-list"), {"url": img, "alt_text": "test image"}
            )
        image_id = response.json()["id"]
        question_2 = Question.objects.create(
            type="subjective",
            item=item_2,
            image=Image.objects.filter(id=image_id).first(),
        )
        question_3 = Question.objects.create(type="checkbox", item=item_3)

        response = self.client.post(
            f"/api/v1/plios/{self.plio_1.uuid}/copy/",
            {"workspace": self.organization.shortcode},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_plio_id = response.data["id"]
        new_plio_uuid = response.data["uuid"]
        new_video_id = response.data["video"]["id"]
        new_item_ids = []
        new_question_ids = []

        for item in response.data.get("items", []):
            new_item_ids.append(item["id"])
            new_question_ids.append(item["details"]["id"])

        # check that the instances are actually created in the given workspace
        connection.set_schema(self.organization.schema_name)

        response = self.client.get(
            f"/api/v1/videos/{new_video_id}/",
            HTTP_ORGANIZATION=self.organization.shortcode,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(
            f"/api/v1/plios/{new_plio_uuid}/",
            HTTP_ORGANIZATION=self.organization.shortcode,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for new_item_id, old_item in zip(new_item_ids, [item_1, item_2, item_3]):
            response = self.client.get(
                f"/api/v1/items/{new_item_id}/",
                HTTP_ORGANIZATION=self.organization.shortcode,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["plio"], new_plio_id)
            self.assertEqual(response.data["type"], old_item.type)
            self.assertEqual(response.data["time"], old_item.time)

        for old_question, new_question_id, new_item_id in zip(
            [question_1, question_2, question_3],
            new_question_ids,
            new_item_ids,
        ):
            response = self.client.get(
                f"/api/v1/questions/{new_question_id}/",
                HTTP_ORGANIZATION=self.organization.shortcode,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["item"], new_item_id)
            self.assertEqual(response.data["type"], old_question.type)

            if old_question.image is not None:
                self.assertEqual(
                    ImageSerializer(old_question.image).data["url"],
                    response.data["image"]["url"],
                )

        # set db connection back to public (default) schema
        connection.set_schema_to_public()

    def test_copying_to_workspace_with_no_video(self):
        plio = Plio.objects.create(
            name="Plio 1", created_by=self.user, status="published"
        )
        response = self.client.post(
            f"/api/v1/plios/{plio.uuid}/copy/",
            {"workspace": self.organization.shortcode},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_plio_uuid = response.data["uuid"]

        # check that the instance is actually created in the given workspace
        connection.set_schema(self.organization.schema_name)

        response = self.client.get(
            f"/api/v1/plios/{new_plio_uuid}/",
            HTTP_ORGANIZATION=self.organization.shortcode,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["video"]["url"], "")

        # set db connection back to public (default) schema
        connection.set_schema_to_public()

    def test_no_metrics_returned_if_no_sessions(self):
        response = self.client.get(
            f"/api/v1/plios/{self.plio_1.uuid}/metrics/",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # if no sessions are there, no metrics will be returned.
        # only whether any survey questions are there will be returned
        self.assertEqual(response.data, {"has_survey_question": False})

    def test_metrics_num_views_and_average_watch_time(self):
        # seed some sessions
        Session.objects.create(plio=self.plio_1, user=self.user, watch_time=10)
        Session.objects.create(plio=self.plio_1, user=self.user, watch_time=20)
        Session.objects.create(plio=self.plio_1, user=self.user_2, watch_time=50)

        response = self.client.get(
            f"/api/v1/plios/{self.plio_1.uuid}/metrics/",
        )
        self.assertEqual(response.data["unique_viewers"], 2)
        self.assertEqual(response.data["average_watch_time"], 35.0)
        self.assertEqual(response.data["percent_one_minute_retention"], None)
        self.assertEqual(response.data["accuracy"], None)
        self.assertEqual(response.data["average_num_answered"], None)
        self.assertEqual(response.data["percent_completed"], None)
        self.assertEqual(response.data["has_survey_question"], False)

    def test_metrics_video_duration_valid_no_valid_retention(self):
        # make the video's duration a valid one for calculating retention
        response = self.client.put(
            f"/api/v1/videos/{self.video.id}/", {"url": self.video.url, "duration": 100}
        )

        # seed some sessions
        Session.objects.create(
            plio=self.plio_1, user=self.user, watch_time=20, retention="NaN,NaN"
        )
        Session.objects.create(plio=self.plio_1, user=self.user_2, watch_time=50)

        response = self.client.get(
            f"/api/v1/plios/{self.plio_1.uuid}/metrics/",
        )

        # retention at 60 seconds should still be None
        self.assertEqual(response.data["percent_one_minute_retention"], 0)
        self.assertEqual(response.data["has_survey_question"], False)

    def test_metrics_video_duration_valid_no_valid_retention_has_questions(self):
        # seed an item
        item = Item.objects.create(type="question", plio=self.plio_1, time=1)

        # seed a question
        Question.objects.create(type="mcq", item=item, text="test")

        # make the video's duration a valid one for calculating retention
        response = self.client.put(
            f"/api/v1/videos/{self.video.id}/", {"url": self.video.url, "duration": 100}
        )

        # seed a session and session answer
        session = Session.objects.create(
            plio=self.plio_1, user=self.user, watch_time=20, retention="NaN,NaN"
        )
        SessionAnswer.objects.create(session=session, item=item)

        response = self.client.get(
            f"/api/v1/plios/{self.plio_1.uuid}/metrics/",
        )

        # retention at 60 seconds should still be None
        self.assertEqual(response.data["percent_one_minute_retention"], 0)
        self.assertEqual(response.data["accuracy"], None)
        self.assertEqual(response.data["average_num_answered"], 0)
        self.assertEqual(response.data["percent_completed"], 0)
        self.assertEqual(response.data["has_survey_question"], False)

    def test_metrics_valid_retention_values(self):
        # make the video's duration a valid one for calculating retention
        import numpy as np

        video_duration = 100
        response = self.client.put(
            f"/api/v1/videos/{self.video.id}/",
            {"url": self.video.url, "duration": video_duration},
        )

        user_3 = User.objects.create(mobile="+919998776655")

        # seed some sessions with valid retention values
        retention_user_1 = [0] * video_duration
        retention_user_1[59:] = np.random.randint(0, 4, video_duration - 59)
        retention_user_1 = ",".join(list(map(str, retention_user_1)))

        retention_user_2 = [0] * video_duration
        retention_user_2[59:] = np.random.randint(0, 4, video_duration - 59)
        retention_user_2 = ",".join(list(map(str, retention_user_2)))

        retention_user_3 = ",".join(["0"] * video_duration)

        Session.objects.create(
            plio=self.plio_1, user=self.user, watch_time=20, retention=retention_user_1
        )
        Session.objects.create(
            plio=self.plio_1,
            user=self.user_2,
            watch_time=50,
            retention=retention_user_2,
        )
        Session.objects.create(
            plio=self.plio_1, user=user_3, watch_time=100, retention=retention_user_3
        )

        response = self.client.get(
            f"/api/v1/plios/{self.plio_1.uuid}/metrics/",
        )

        # retention at 60 seconds should still be None
        self.assertEqual(response.data["percent_one_minute_retention"], 66.67)
        self.assertEqual(response.data["has_survey_question"], False)

    def test_question_metrics_with_single_session_no_answer(self):
        # seed an item
        item = Item.objects.create(type="question", plio=self.plio_1, time=1)

        # seed a question
        Question.objects.create(type="mcq", item=item, text="test")

        # seed a session and session answer
        session = Session.objects.create(
            plio=self.plio_1, user=self.user, watch_time=20
        )
        SessionAnswer.objects.create(session=session, item=item)

        response = self.client.get(
            f"/api/v1/plios/{self.plio_1.uuid}/metrics/",
        )
        self.assertEqual(response.data["average_num_answered"], 0)
        self.assertEqual(response.data["percent_completed"], 0)
        self.assertEqual(response.data["accuracy"], None)

    def test_question_metrics_with_multiple_sessions_no_answer(self):
        # seed an item
        item = Item.objects.create(type="question", plio=self.plio_1, time=1)

        # seed a question
        Question.objects.create(type="mcq", item=item, text="test")

        # seed a few session and session answer objects with empty answers
        session = Session.objects.create(
            plio=self.plio_1, user=self.user, watch_time=20
        )
        SessionAnswer.objects.create(session=session, item=item)

        session_2 = Session.objects.create(
            plio=self.plio_1, user=self.user_2, watch_time=40
        )
        SessionAnswer.objects.create(session=session_2, item=item)

        response = self.client.get(
            f"/api/v1/plios/{self.plio_1.uuid}/metrics/",
        )
        self.assertEqual(response.data["average_num_answered"], 0)
        self.assertEqual(response.data["percent_completed"], 0)
        self.assertEqual(response.data["accuracy"], None)
        self.assertEqual(response.data["has_survey_question"], False)

    def test_question_metrics_answers_provided(self):
        # seed items
        item_1 = Item.objects.create(type="question", plio=self.plio_1, time=1)
        item_2 = Item.objects.create(type="question", plio=self.plio_1, time=10)
        item_3 = Item.objects.create(type="question", plio=self.plio_1, time=20)

        # seed questions
        Question.objects.create(
            type="mcq",
            item=item_1,
            text="test",
            options=["", ""],
            correct_answer=0,
        )
        Question.objects.create(
            type="checkbox",
            item=item_2,
            text="test",
            options=["", ""],
            correct_answer=[0, 1],
        )
        Question.objects.create(
            type="subjective",
            item=item_3,
            text="test",
        )

        # seed a few session and session answer objects with answers
        session = Session.objects.create(
            plio=self.plio_1, user=self.user, watch_time=20
        )
        SessionAnswer.objects.create(session=session, item=item_1, answer=0)
        SessionAnswer.objects.create(session=session, item=item_2, answer=[1])
        SessionAnswer.objects.create(session=session, item=item_3, answer="abcd")

        session_2 = Session.objects.create(
            plio=self.plio_1, user=self.user_2, watch_time=40
        )
        SessionAnswer.objects.create(session=session_2, item=item_1, answer=1)
        SessionAnswer.objects.create(session=session_2, item=item_2, answer=[0, 1])
        SessionAnswer.objects.create(session=session_2, item=item_3)

        response = self.client.get(
            f"/api/v1/plios/{self.plio_1.uuid}/metrics/",
        )
        self.assertEqual(response.data["average_num_answered"], 2)
        self.assertEqual(response.data["percent_completed"], 50)
        self.assertEqual(response.data["accuracy"], 58.33)
        self.assertEqual(response.data["has_survey_question"], False)

    def test_survey_mode_returned_correctly_if_no_sessions(self):
        # seed items
        item_1 = Item.objects.create(type="question", plio=self.plio_1, time=1)

        # seed questions
        Question.objects.create(
            type="mcq",
            item=item_1,
            text="test",
            options=["", ""],
            correct_answer=0,
            survey=True,
        )

        response = self.client.get(
            f"/api/v1/plios/{self.plio_1.uuid}/metrics/",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"has_survey_question": True})

    def test_question_metrics_calculated_using_non_survey_questions(self):
        # seed items
        item_1 = Item.objects.create(type="question", plio=self.plio_1, time=1)
        item_2 = Item.objects.create(type="question", plio=self.plio_1, time=10)
        item_3 = Item.objects.create(type="question", plio=self.plio_1, time=20)

        # seed questions
        Question.objects.create(
            type="mcq",
            item=item_1,
            text="test",
            options=["", ""],
            correct_answer=0,
        )
        Question.objects.create(
            type="checkbox",
            item=item_2,
            text="test",
            options=["", ""],
            correct_answer=[0, 1],
        )
        Question.objects.create(
            type="subjective",
            item=item_3,
            text="test",
            survey=True,
        )

        # seed a few session and session answer objects with answers
        session = Session.objects.create(
            plio=self.plio_1, user=self.user, watch_time=20
        )
        SessionAnswer.objects.create(session=session, item=item_1, answer=0)
        SessionAnswer.objects.create(session=session, item=item_2, answer=[1])
        SessionAnswer.objects.create(session=session, item=item_3, answer="abcd")

        session_2 = Session.objects.create(
            plio=self.plio_1, user=self.user_2, watch_time=40
        )
        SessionAnswer.objects.create(session=session_2, item=item_1, answer=1)
        SessionAnswer.objects.create(session=session_2, item=item_2, answer=[0, 1])
        SessionAnswer.objects.create(session=session_2, item=item_3)

        response = self.client.get(
            f"/api/v1/plios/{self.plio_1.uuid}/metrics/",
        )
        self.assertEqual(response.data["average_num_answered"], 2)
        self.assertEqual(response.data["percent_completed"], 100)
        self.assertEqual(response.data["accuracy"], 50)
        self.assertEqual(response.data["has_survey_question"], True)

    def test_all_question_metrics_None_if_all_questions_survey(self):
        # seed items
        item_1 = Item.objects.create(type="question", plio=self.plio_1, time=1)
        item_2 = Item.objects.create(type="question", plio=self.plio_1, time=10)
        item_3 = Item.objects.create(type="question", plio=self.plio_1, time=20)

        # seed questions
        Question.objects.create(
            type="mcq",
            item=item_1,
            text="test",
            options=["", ""],
            correct_answer=0,
            survey=True,
        )
        Question.objects.create(
            type="checkbox",
            item=item_2,
            text="test",
            options=["", ""],
            correct_answer=[0, 1],
            survey=True,
        )
        Question.objects.create(
            type="subjective",
            item=item_3,
            text="test",
            survey=True,
        )

        # seed a few session and session answer objects with answers
        session = Session.objects.create(
            plio=self.plio_1, user=self.user, watch_time=20
        )
        SessionAnswer.objects.create(session=session, item=item_1, answer=0)
        SessionAnswer.objects.create(session=session, item=item_2, answer=[1])
        SessionAnswer.objects.create(session=session, item=item_3, answer="abcd")

        session_2 = Session.objects.create(
            plio=self.plio_1, user=self.user_2, watch_time=40
        )
        SessionAnswer.objects.create(session=session_2, item=item_1, answer=1)
        SessionAnswer.objects.create(session=session_2, item=item_2, answer=[0, 1])
        SessionAnswer.objects.create(session=session_2, item=item_3)

        response = self.client.get(
            f"/api/v1/plios/{self.plio_1.uuid}/metrics/",
        )

        self.assertEqual(response.data["unique_viewers"], 2)
        self.assertEqual(response.data["average_watch_time"], 30.0)
        self.assertEqual(response.data["average_num_answered"], None)
        self.assertEqual(response.data["percent_completed"], None)
        self.assertEqual(response.data["accuracy"], None)
        self.assertEqual(response.data["has_survey_question"], True)


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
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_can_download_data_for_other_user_plio_in_organization(self):

        OrganizationUser.objects.create(
            organization=self.organization, user=self.user, role=self.org_admin_role
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

    def test_updating_video_updates_linked_plio_instance_cache(self):
        # create a video
        video_title = "Video for cache"
        video = Video.objects.create(
            title=video_title, url="https://www.youtube.com/watch?v=vnISjBbrMUM"
        )
        # create a plio with the video
        plio = Plio.objects.create(
            name="Plio for cache", video=video, created_by=self.user
        )

        # there shouldn't be any cache as we created plio without API
        cache_key_name = get_cache_key(plio)
        self.assertEqual(len(cache.keys(cache_key_name)), 0)

        # request plio again via API to generate cache
        self.client.get(reverse("plios-detail", kwargs={"uuid": plio.uuid}))

        # plio cache should exist now
        self.assertEqual(len(cache.keys(cache_key_name)), 1)
        self.assertEqual(cache.get(cache_key_name)["video"]["title"], video_title)

        # update video title
        new_title_for_video = "New title for cache"
        self.client.patch(
            reverse("videos-detail", kwargs={"pk": video.id}),
            {"title": new_title_for_video},
        )

        # plio cache should be deleted after video update
        self.assertEqual(len(cache.keys(cache_key_name)), 0)

        # re-request plio again via API after video update
        self.client.get(reverse("plios-detail", kwargs={"uuid": plio.uuid}))

        # check plio cache with the new video title
        self.assertEqual(
            cache.get(cache_key_name)["video"]["title"], new_title_for_video
        )


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

    def test_deleting_plio_deletes_items(self):
        """Deleting a plio should delete the items associated with it"""
        # fetching the created item works at first
        response = self.client.get(f"/api/v1/items/{self.item.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # delete the plio associated with the item
        response = self.client.delete(f"/api/v1/plios/{self.plio.uuid}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # fetching the item should now give an error
        response = self.client.get(f"/api/v1/items/{self.item.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_updating_item_updates_linked_plio_instance_cache(self):
        # create a plio
        plio = Plio.objects.create(
            name="Plio for cache", video=self.video, created_by=self.user
        )
        item_time = 1
        # create an item for the plio
        item = Item.objects.create(type="question", plio=plio, time=item_time)

        # there shouldn't be any cache as we created plio without API
        cache_key_name = get_cache_key(plio)
        self.assertEqual(len(cache.keys(cache_key_name)), 0)

        # request plio again via API to generate cache
        self.client.get(reverse("plios-detail", kwargs={"uuid": plio.uuid}))

        # plio cache should exist now
        self.assertEqual(len(cache.keys(cache_key_name)), 1)
        self.assertEqual(cache.get(cache_key_name)["items"][0]["time"], item_time)

        # update item time
        item_new_time = 100
        self.client.patch(
            reverse("items-detail", kwargs={"pk": item.id}),
            {"time": item_new_time},
        )

        # plio cache should be deleted after item time update
        self.assertEqual(len(cache.keys(cache_key_name)), 0)

        # re-request plio again via API after item update
        self.client.get(reverse("plios-detail", kwargs={"uuid": plio.uuid}))

        # check plio cache with the update item time
        self.assertEqual(cache.get(cache_key_name)["items"][0]["time"], item_new_time)

    def test_bulk_delete_fails_without_id(self):
        response = self.client.delete("/api/v1/items/bulk_delete/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(response.data["detail"], "item id(s) not provided")

    def test_bulk_delete_fails_with_non_list_id(self):
        response = self.client.delete("/api/v1/items/bulk_delete/", {"id": 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(
            response.data["detail"],
            "id should contain a list of item ids to be deleted",
        )

    def test_bulk_delete_fails_with_non_existing_item_ids(self):
        response = self.client.delete(
            "/api/v1/items/bulk_delete/",
            json.dumps({"id": [self.item.id, 100]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data["detail"], "one or more of the ids provided do not exist"
        )

    def test_bulk_delete(self):
        # create a few more items and associate with different plios
        item_2 = Item.objects.create(type="question", plio=self.plio, time=10)
        plio = Plio.objects.create(
            name="Plio 2", video=self.video, created_by=self.user
        )
        item_3 = Item.objects.create(type="question", plio=plio, time=20)

        item_ids = [self.item.id, item_2.id, item_3.id]

        response = self.client.delete(
            "/api/v1/items/bulk_delete/",
            json.dumps({"id": item_ids}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for item_id in item_ids:
            response = self.client.get(f"/api/v1/items/{item_id}/")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


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

    def test_deleting_plio_deletes_questions(self):
        """Deleting a plio should delete the questions associated with it"""
        # fetching the created question works at first
        response = self.client.get(f"/api/v1/questions/{self.question.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # delete the plio associated with the question
        response = self.client.delete(f"/api/v1/plios/{self.plio.uuid}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # fetching the question should now give an error
        response = self.client.get(f"/api/v1/questions/{self.question.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_updating_question_updates_linked_plio_instance_cache(self):
        # create a plio
        plio = Plio.objects.create(
            name="Plio for cache", video=self.video, created_by=self.user
        )
        # create an item for the plio
        item = Item.objects.create(type="question", plio=plio, time=1)

        # create a question for the item
        question_text = "Question for cache"
        question = Question.objects.create(type="mcq", item=item, text=question_text)

        # there shouldn't be any cache as we created plio without API
        cache_key_name = get_cache_key(plio)
        self.assertEqual(len(cache.keys(cache_key_name)), 0)

        # request plio again via API to generate cache
        self.client.get(reverse("plios-detail", kwargs={"uuid": plio.uuid}))

        # plio cache should exist now
        self.assertEqual(len(cache.keys(cache_key_name)), 1)
        self.assertEqual(
            cache.get(cache_key_name)["items"][0]["details"]["text"], question_text
        )

        # update question text
        question_new_text = "Updated Text for Question"
        self.client.patch(
            reverse("questions-detail", kwargs={"pk": question.id}),
            {"text": question_new_text},
        )

        # plio cache should be deleted after question text update
        self.assertEqual(len(cache.keys(cache_key_name)), 0)

        # re-request plio again via API after question update
        self.client.get(reverse("plios-detail", kwargs={"uuid": plio.uuid}))

        # check plio cache with the updated question text
        self.assertEqual(
            cache.get(cache_key_name)["items"][0]["details"]["text"], question_new_text
        )

    def test_deleting_question_deletes_linked_image(self):
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

        # delete question
        response = self.client.delete(f"/api/v1/questions/{self.question.id}/")

        # the image should be deleted as well
        response = self.client.get(f"/api/v1/images/{image_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


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
