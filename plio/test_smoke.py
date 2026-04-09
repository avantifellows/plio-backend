"""
Runtime smoke tests for Django 3.2 migration validation (US-010).

Covers integration points not exercised by existing app-level tests:
- Admin panel accessibility and login
- /api/v1/docs/ schema generation (drf-yasg)
- /silk/ route accessibility
- /auth/ OAuth2 social auth routes
- Plio list with unique_viewers annotation (with actual sessions)
- Session create/retrieve with SessionAnswer reverse-relation ordering
"""

from django.test import TestCase, override_settings
from django.urls import reverse, resolve
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import status

from plio.tests import BaseTestCase, get_new_access_token
from plio.models import Plio, Video, Item, Question
from entries.models import Session, SessionAnswer
from users.models import OrganizationUser

User = get_user_model()


class AdminSmokeTestCase(TestCase):
    """Verify the Django admin panel is accessible and login works."""

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin@test.com", password="testpass123"
        )

    def test_admin_login_page_loads(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_login_works(self):
        logged_in = self.client.login(email="admin@test.com", password="testpass123")
        self.assertTrue(logged_in)

    def test_admin_index_accessible_after_login(self):
        self.client.login(email="admin@test.com", password="testpass123")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_redirects_unauthenticated(self):
        response = self.client.get("/admin/")
        # Django 3.2 admin catch-all redirects to login
        self.assertIn(response.status_code, [301, 302])


class DocsSmokeTestCase(TestCase):
    """Verify /api/v1/docs/ loads and generates schema via drf-yasg."""

    def test_docs_endpoint_loads(self):
        response = self.client.get("/api/v1/docs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_docs_url_resolves(self):
        match = resolve("/api/v1/docs/")
        self.assertEqual(match.url_name, "schema-redoc")


class SilkSmokeTestCase(TestCase):
    """Verify /silk/ route is accessible."""

    def test_silk_url_resolves(self):
        match = resolve("/silk/")
        self.assertIsNotNone(match)

    @override_settings(SILKY_AUTHENTICATION=False, SILKY_AUTHORISATION=False)
    def test_silk_route_accessible(self):
        response = self.client.get("/silk/")
        # silk may redirect to /silk/ with trailing slash or return 200/301/302
        self.assertIn(response.status_code, [200, 301, 302])


class AuthRoutesSmokeTestCase(TestCase):
    """Verify /auth/ OAuth2 social auth routes resolve correctly."""

    def test_auth_token_url_resolves(self):
        """The /auth/token route from rest_framework_social_oauth2 resolves."""
        match = resolve("/auth/token")
        self.assertIsNotNone(match)

    def test_auth_convert_token_url_resolves(self):
        """The /auth/convert-token route resolves."""
        match = resolve("/auth/convert-token")
        self.assertIsNotNone(match)

    def test_auth_revoke_token_url_resolves(self):
        """The /auth/revoke-token route resolves."""
        match = resolve("/auth/revoke-token")
        self.assertIsNotNone(match)


class PlioListAnnotationSmokeTestCase(BaseTestCase):
    """Verify the Plio list endpoint returns correct unique_viewers counts
    when actual sessions exist. This exercises the Subquery/annotate query
    that is sensitive to Django 3.2's stricter GROUP BY handling."""

    def setUp(self):
        super().setUp()
        self.video = Video.objects.create(
            title="Video 1",
            url="https://www.youtube.com/watch?v=vnISjBbrMUM",
            duration=10,
        )
        self.plio = Plio.objects.create(
            name="Plio 1",
            video=self.video,
            created_by=self.user,
            status="published",
        )

    def test_unique_viewers_zero_when_no_sessions(self):
        response = self.client.get("/api/v1/plios/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["unique_viewers"], 0)

    def test_unique_viewers_counts_distinct_users(self):
        # Create sessions from two different users
        Session.objects.create(plio=self.plio, user=self.user)
        Session.objects.create(plio=self.plio, user=self.user_2)
        # Duplicate session from user 1 should not increase count
        Session.objects.create(plio=self.plio, user=self.user)

        response = self.client.get("/api/v1/plios/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["unique_viewers"], 2)

    def test_unique_viewers_single_user(self):
        Session.objects.create(plio=self.plio, user=self.user)

        response = self.client.get("/api/v1/plios/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["unique_viewers"], 1)

    def test_video_url_annotation(self):
        response = self.client.get("/api/v1/plios/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["video_url"], self.video.url)


class SessionAnswerOrderingSmokeTestCase(BaseTestCase):
    """Verify that SessionAnswer reverse-relation ordering works correctly
    after the Django 3.2 upgrade. SessionAnswer and Question both use
    Meta.ordering = ['item__time'], and this cross-FK ordering is sensitive
    to Django 3.2's stricter GROUP BY handling."""

    def setUp(self):
        super().setUp()
        self.video = Video.objects.create(
            title="Video 1",
            url="https://www.youtube.com/watch?v=vnISjBbrMUM",
            duration=10,
        )
        self.plio = Plio.objects.create(
            name="Plio 1",
            video=self.video,
            created_by=self.user,
            status="published",
        )
        # Create items at different times (ordering matters)
        self.item_1 = Item.objects.create(type="question", plio=self.plio, time=1)
        self.item_2 = Item.objects.create(type="question", plio=self.plio, time=5)
        self.item_3 = Item.objects.create(type="question", plio=self.plio, time=3)

    def test_session_answers_ordered_by_item_time(self):
        """Session answers should be ordered by item__time (1, 3, 5)."""
        response = self.client.post(reverse("sessions-list"), {"plio": self.plio.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        answers = response.data["session_answers"]
        self.assertEqual(len(answers), 3)

        # Verify ordering: item times should be 1, 3, 5
        answer_item_ids = [a["item_id"] for a in answers]
        self.assertEqual(answer_item_ids[0], self.item_1.id)  # time=1
        self.assertEqual(answer_item_ids[1], self.item_3.id)  # time=3
        self.assertEqual(answer_item_ids[2], self.item_2.id)  # time=5

    def test_session_retrieve_preserves_answer_ordering(self):
        """Retrieving a session preserves the SessionAnswer ordering."""
        create_response = self.client.post(
            reverse("sessions-list"), {"plio": self.plio.id}
        )
        session_id = create_response.data["id"]

        retrieve_response = self.client.get(
            reverse("sessions-detail", args=[session_id])
        )
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        answers = retrieve_response.data["session_answers"]

        answer_item_ids = [a["item_id"] for a in answers]
        self.assertEqual(answer_item_ids[0], self.item_1.id)  # time=1
        self.assertEqual(answer_item_ids[1], self.item_3.id)  # time=3
        self.assertEqual(answer_item_ids[2], self.item_2.id)  # time=5


class OrgWorkspaceSmokeTestCase(BaseTestCase):
    """Verify multi-tenancy organization switching works with the
    HTTP_ORGANIZATION header after the Django 3.2 upgrade."""

    def setUp(self):
        super().setUp()
        # Add user to org
        OrganizationUser.objects.create(
            organization=self.organization,
            user=self.user,
            role=self.org_view_role,
        )

    def test_org_header_switches_schema(self):
        """Requests with HTTP_ORGANIZATION header access org-specific data."""
        # Create data in org schema
        connection.set_schema(self.organization.schema_name)
        video_org = Video.objects.create(
            title="Org Video",
            url="https://www.youtube.com/watch?v=orgvideo",
        )
        Plio.objects.create(name="Org Plio", video=video_org, created_by=self.user)
        connection.set_schema_to_public()

        # Request with org header
        self.client.credentials(
            HTTP_ORGANIZATION=self.organization.shortcode,
            HTTP_AUTHORIZATION="Bearer " + self.access_token.token,
        )
        response = self.client.get("/api/v1/plios/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Org Plio")

    def test_public_schema_without_org_header(self):
        """Requests without HTTP_ORGANIZATION header use public schema."""
        # Ensure we're on the public schema
        connection.set_schema_to_public()

        # Create plio in public schema
        video = Video.objects.create(
            title="Public Video",
            url="https://www.youtube.com/watch?v=pubvideo",
        )
        Plio.objects.create(name="Public Plio", video=video, created_by=self.user)

        response = self.client.get("/api/v1/plios/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Public Plio")
