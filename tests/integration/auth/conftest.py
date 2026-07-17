import pytest
from django.conf import settings
from oauth2_provider.models import Application
from rest_framework.test import APIClient

# A known plaintext client secret for the convert-token confidential client.
# drf-social-oauth2's convert-token view injects the STORED secret into the
# token request, so the application must keep it retrievable plaintext
# (hash_client_secret=False) — mirroring createoauth2application.
CONVERT_TOKEN_CLIENT_SECRET = "convert-token-test-secret"


@pytest.fixture
def api_application(db):
    """The single oauth2 application internal tokens are minted against.

    Mirrors the boot-time seed named by ``API_APPLICATION_NAME`` so that
    ``login_user_and_get_access_token`` (used by the OTP and SSO views) can
    resolve exactly one application regardless of how the lane is invoked.
    """
    return Application.objects.get_or_create(
        name=settings.API_APPLICATION_NAME,
        defaults={
            "redirect_uris": "",
            "client_type": Application.CLIENT_CONFIDENTIAL,
            "authorization_grant_type": Application.GRANT_AUTHORIZATION_CODE,
            "hash_client_secret": False,
        },
    )[0]


@pytest.fixture
def convert_token_app(api_application):
    """The confidential client the convert-token exchange authenticates against.

    Returns ``(application, plaintext_secret)``. The application is forced to
    hash_client_secret=False regardless of which conftest seeded the row —
    drf-social-oauth2 injects the stored secret into the token request, so
    convert-token only works with a plaintext-at-rest secret.
    """
    api_application.hash_client_secret = False
    api_application.client_secret = CONVERT_TOKEN_CLIENT_SECRET
    api_application.save()
    return api_application, CONVERT_TOKEN_CLIENT_SECRET


@pytest.fixture
def bearer_client():
    """Builds an APIClient authenticated with the given internal access token.

    Used to prove a login flow's issued token works against a real authenticated
    endpoint, without inspecting the token internals.
    """

    def _build(access_token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        return client

    return _build
