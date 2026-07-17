"""Third-party SSO login journeys.

No mocks: the endpoint is a plain ``AllowAny`` route. An org's ``api_key`` (seeded
by the tenant-universe fixtures) mints a user scoped to that org. Cross-org
isolation is owned by the org/tenancy slice and is out of scope here.
"""
from django.urls import reverse
from rest_framework import status

from users.models import User

SSO_URL = reverse("generate_external_auth_access_token")


def test_sso_mints_org_scoped_user_with_working_token(
    client, api_application, org_a, bearer_client
):
    response = client.post(
        SSO_URL, {"unique_id": "learner-42", "api_key": org_a.api_key}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["token_type"] == "Bearer"

    # the minted user is scoped to the org whose api_key was used
    minted = User.objects.get(unique_id="learner-42", auth_org=org_a)
    assert minted.auth_org_id == org_a.id

    # the returned token works on a subsequent authenticated request
    authed = bearer_client(response.data["access_token"])
    assert authed.get("/api/v1/plios/").status_code == status.HTTP_200_OK


def test_sso_returning_user_is_not_duplicated(client, api_application, org_a):
    payload = {"unique_id": "learner-99", "api_key": org_a.api_key}

    first = client.post(SSO_URL, payload)
    second = client.post(SSO_URL, payload)

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    # the same (unique_id, org) pair logs in again without a duplicate user
    assert User.objects.filter(unique_id="learner-99", auth_org=org_a).count() == 1


def test_sso_rejects_invalid_api_key(client, api_application, org_a):
    response = client.post(
        SSO_URL, {"unique_id": "learner-42", "api_key": "not-a-real-api-key"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(unique_id="learner-42").exists()


def test_sso_rejects_missing_required_keys(client, db):
    missing_api_key = client.post(SSO_URL, {"unique_id": "learner-42"})
    assert missing_api_key.status_code == status.HTTP_400_BAD_REQUEST
    assert missing_api_key.data["detail"] == "api_key not provided."

    missing_unique_id = client.post(SSO_URL, {"api_key": "some-api-key"})
    assert missing_unique_id.status_code == status.HTTP_400_BAD_REQUEST
    assert missing_unique_id.data["detail"] == "unique_id not provided."
