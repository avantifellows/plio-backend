"""Google convert-token journeys.

Only Google's outbound HTTP endpoints are stubbed; the whole internal pipeline
(social-auth backend -> drf-social-oauth2 -> user creation -> internal token
issuance) runs for real. ``responses.activate`` makes any un-stubbed outbound
request raise, so these specs cannot reach the external network.
"""
import responses
from rest_framework import status

from users.models import User

GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def google_userinfo(email, sub):
    """A minimal Google OpenID userinfo payload for a signed-in account."""
    return {
        "sub": sub,
        "email": email,
        "email_verified": True,
        "given_name": "Ada",
        "family_name": "Lovelace",
        "name": "Ada Lovelace",
        "picture": "https://example.com/ada.png",
    }


def convert_token_payload(app, secret, google_token="google-access-token"):
    return {
        "grant_type": "convert_token",
        "client_id": app.client_id,
        "client_secret": secret,
        "backend": "google-oauth2",
        "token": google_token,
    }


@responses.activate
def test_convert_token_creates_new_user_and_issues_working_token(
    client, convert_token_app, bearer_client
):
    app, secret = convert_token_app
    responses.add(
        responses.GET,
        GOOGLE_USERINFO_URL,
        json=google_userinfo("ada@example.com", "google-sub-1"),
        status=status.HTTP_200_OK,
    )

    response = client.post("/auth/convert-token/", convert_token_payload(app, secret))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["token_type"] == "Bearer"
    assert User.objects.filter(email="ada@example.com").count() == 1

    # the issued token is proven by using it against a real authenticated endpoint
    authed = bearer_client(response.data["access_token"])
    assert authed.get("/api/v1/plios/").status_code == status.HTTP_200_OK


@responses.activate
def test_convert_token_returning_user_is_not_duplicated(client, convert_token_app):
    app, secret = convert_token_app
    responses.add(
        responses.GET,
        GOOGLE_USERINFO_URL,
        json=google_userinfo("grace@example.com", "google-sub-2"),
        status=status.HTTP_200_OK,
    )

    first = client.post("/auth/convert-token/", convert_token_payload(app, secret))
    second = client.post("/auth/convert-token/", convert_token_payload(app, secret))

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    # the same Google identity logs in again without creating a duplicate user
    assert User.objects.filter(email="grace@example.com").count() == 1


@responses.activate
def test_convert_token_logs_in_pre_created_email_user_without_duplicating(
    client, convert_token_app
):
    """A user pre-created by email (admin provisioning, e2e seed) must be able
    to log in via convert-token: user.email is unique, so the pipeline's
    create_user hits IntegrityError and must recover by adopting the existing
    row -- social-auth-app-django 5.8.0 broke this recovery (caught by the
    e2e suite on the Django 5.1 rung as a 400 "account already in use")."""
    app, secret = convert_token_app
    pre_created = User.objects.create(email="ada@example.com", first_name="Pre")
    responses.add(
        responses.GET,
        GOOGLE_USERINFO_URL,
        json=google_userinfo("ada@example.com", "google-sub-precreated"),
        status=status.HTTP_200_OK,
    )

    response = client.post("/auth/convert-token/", convert_token_payload(app, secret))

    assert response.status_code == status.HTTP_200_OK
    assert User.objects.filter(email="ada@example.com").count() == 1
    assert response.data["user"]["email"] == pre_created.email
