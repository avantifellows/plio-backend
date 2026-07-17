"""Fixtures for the org/tenancy journey specs.

Actors and plios here are built through the shared harness (``authed_client``,
``in_workspace``, factories) so the specs never touch ``connection.set_schema()``.
Tenancy is exercised exclusively through the ``Organization`` request header.
"""
import pytest
from django.conf import settings
from django.urls import reverse
from oauth2_provider.models import Application
from rest_framework.test import APIClient

from tests.actors import Actor
from tests.builders import in_workspace
from tests.factories import PlioFactory
from users.models import OrganizationUser, Role


@pytest.fixture
def matrix_actor(authed_client, org_a):
    """Builds an actor for a permission-matrix role.

    ``member`` belongs to org-a (role ``org-view``); ``non_member`` belongs to
    no organization; ``superuser`` has ``is_superuser`` set. None of them owns
    the plios under test, so access is decided purely by role, workspace and
    visibility rather than by ownership.
    """

    def _for(role):
        actor = authed_client()
        if role == "member":
            OrganizationUser.objects.create(
                user=actor.user,
                organization=org_a,
                role=Role.objects.get(name="org-view"),
            )
        elif role == "superuser":
            actor.user.is_superuser = True
            actor.user.save()
        elif role != "non_member":
            raise ValueError("unknown matrix role: {}".format(role))
        return actor

    return _for


@pytest.fixture
def owner(authed_client):
    """The user who owns every plio under test; never the acting actor."""
    return authed_client()


@pytest.fixture
def make_plio(owner, org_a):
    """Creates a plio owned by ``owner`` in the workspace with the visibility asked.

    ``workspace="org"`` places it in org-a's schema; ``workspace="personal"``
    places it in the public schema requests land in with no ``Organization``
    header. The builder owns the schema switch so specs stay header-only.
    """

    def _make(workspace, visibility):
        is_public = visibility == "public"
        if workspace == "org":
            with in_workspace(org_a):
                return PlioFactory(created_by=owner.user, is_public=is_public)
        return PlioFactory(created_by=owner.user, is_public=is_public)

    return _make


@pytest.fixture
def api_application(db):
    """The oauth2 application internal tokens are minted against.

    Mirrors the boot-time seed named by ``API_APPLICATION_NAME`` so the SSO
    exchange can resolve exactly one application regardless of how the lane is
    invoked (the session-level seed only fires on the pure integration lane).
    """
    return Application.objects.get_or_create(
        name=settings.API_APPLICATION_NAME,
        defaults={
            "redirect_uris": "",
            "client_type": Application.CLIENT_CONFIDENTIAL,
            "authorization_grant_type": Application.GRANT_AUTHORIZATION_CODE,
        },
    )[0]


@pytest.fixture
def sso_login(client, api_application):
    """Logs a learner in through the real SSO endpoint for the given org.

    Returns an :class:`Actor` wrapping the minted token so cross-org access can
    be probed through the same header-driven request idiom as every other spec.
    """
    from users.models import User

    sso_url = reverse("generate_external_auth_access_token")

    def _login(unique_id, organization):
        response = client.post(
            sso_url, {"unique_id": unique_id, "api_key": organization.api_key}
        )
        assert response.status_code == 200, response.data
        token = response.data["access_token"]
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION="Bearer " + token)
        user = User.objects.get(unique_id=unique_id, auth_org=organization)
        return Actor(api, user)

    return _login
