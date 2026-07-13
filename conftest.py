import datetime
import uuid

import pytest
from django.conf import settings
from django.db import connection
from django.utils import timezone
from django_redis import get_redis_connection
from oauth2_provider.models import AccessToken, Application
from rest_framework.test import APIClient

from organizations.models import Organization
from tests.actors import Actor
from tests.factories import UserFactory
from users.models import OrganizationUser, Role


def ensure_api_application():
    return Application.objects.get_or_create(
        name=settings.API_APPLICATION_NAME,
        defaults={
            "redirect_uris": "",
            "client_type": Application.CLIENT_CONFIDENTIAL,
            "authorization_grant_type": Application.GRANT_AUTHORIZATION_CODE,
        },
    )[0]


def pytest_collection_modifyitems(items):
    integration = pytest.mark.integration
    for item in items:
        if "/tests/integration/" in str(item.fspath):
            item.add_marker(integration)


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker, request):
    with django_db_blocker.unblock():
        for role in settings.DEFAULT_ROLES:
            Role.objects.get_or_create(name=role["name"])
        Organization.objects.get_or_create(
            shortcode="org-a", defaults={"name": "Org A", "schema_name": "org_a"}
        )
        Organization.objects.get_or_create(
            shortcode="org-b", defaults={"name": "Org B", "schema_name": "org_b"}
        )
        if settings.DEFAULT_TENANT_SHORTCODE:
            # production maps the default shortcode to the public schema via
            # `createtenant` (docs/ENV.md "default tenant"); mirror that row so
            # no-header journeys resolve the configured default tenant instead
            # of silently passing through the unknown-tenant fallback
            Organization.objects.get_or_create(
                shortcode=settings.DEFAULT_TENANT_SHORTCODE,
                defaults={"name": "Personal workspace", "schema_name": "public"},
            )
        if all(
            item.get_closest_marker("integration") for item in request.session.items
        ):
            ensure_api_application()
        connection.set_schema_to_public()


@pytest.fixture(autouse=True)
def clean_redis():
    # flush before the test too: a run interrupted before teardown leaves
    # stale keys behind, and the recreated test database reuses low primary
    # keys, so a stale tenant cache entry could serve the next run's first read
    get_redis_connection("default").flushdb()
    yield
    get_redis_connection("default").flushdb()
    connection.set_schema_to_public()


@pytest.fixture(scope="session")
def org_a(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return Organization.objects.get(shortcode="org-a")


@pytest.fixture(scope="session")
def org_b(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return Organization.objects.get(shortcode="org-b")


@pytest.fixture
def authed_client(db):
    application = ensure_api_application()

    def create(user=None):
        user = user or UserFactory()
        token = AccessToken.objects.create(
            user=user,
            application=application,
            token=uuid.uuid4().hex,
            expires=timezone.now() + datetime.timedelta(days=1),
            scope="read write",
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer " + token.token)
        return Actor(client, user)

    return create


@pytest.fixture
def creator(authed_client, org_a, org_b):
    actor = authed_client()
    role = Role.objects.get(name="org-view")
    OrganizationUser.objects.create(user=actor.user, organization=org_a, role=role)
    OrganizationUser.objects.create(user=actor.user, organization=org_b, role=role)
    return actor


@pytest.fixture
def learner(authed_client):
    return authed_client()
