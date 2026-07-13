"""OTP-over-SMS login journeys.

The OTP is read in-process from the database (never from an SMS). ``SMS_DRIVER``
is unset in test settings, so the SNS publish path is dead by default; one spec
flips it on with a botocore-stubbed client to prove no live AWS call is possible.
"""
import datetime

import boto3
import pytest
from botocore.stub import Stubber
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

import users.services as user_services
import users.views as user_views
from users.models import OneTimePassword, User

REQUEST_URL = reverse("request-otp")
VERIFY_URL = reverse("verify-otp")


def latest_otp(mobile):
    return OneTimePassword.objects.filter(mobile=mobile).order_by("-id").first()


def test_otp_request_then_verify_creates_user_and_issues_working_token(
    client, api_application, bearer_client
):
    mobile = "+919000000001"

    request_response = client.post(REQUEST_URL, {"mobile": mobile})
    assert request_response.status_code == status.HTTP_200_OK

    # the OTP is read in-process from the database, not from an SMS
    otp = latest_otp(mobile)
    verify_response = client.post(VERIFY_URL, {"mobile": mobile, "otp": otp.otp})

    assert verify_response.status_code == status.HTTP_200_OK
    assert verify_response.data["token_type"] == "Bearer"
    assert User.objects.filter(mobile=mobile).count() == 1

    authed = bearer_client(verify_response.data["access_token"])
    assert authed.get("/api/v1/plios/").status_code == status.HTTP_200_OK


def test_otp_verify_fails_for_expired_otp(client, db):
    mobile = "+919000000002"
    # construct an already-expired OTP row directly rather than sleeping
    OneTimePassword.objects.create(
        mobile=mobile,
        otp="123456",
        expires_at=timezone.now() - datetime.timedelta(seconds=1),
    )

    response = client.post(VERIFY_URL, {"mobile": mobile, "otp": "123456"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    # no user is minted from an expired OTP
    assert not User.objects.filter(mobile=mobile).exists()


def test_otp_re_request_issues_fresh_usable_otp(client, api_application):
    mobile = "+919000000003"

    client.post(REQUEST_URL, {"mobile": mobile})
    client.post(REQUEST_URL, {"mobile": mobile})

    # re-requesting yields a second, independent OTP row
    assert OneTimePassword.objects.filter(mobile=mobile).count() == 2

    # the freshly requested OTP verifies successfully
    fresh_otp = latest_otp(mobile)
    response = client.post(VERIFY_URL, {"mobile": mobile, "otp": fresh_otp.otp})
    assert response.status_code == status.HTTP_200_OK


def test_otp_request_does_not_touch_sns_when_driver_unset(client, db, monkeypatch):
    # SMS_DRIVER is unset in test settings; the SNS service must never be built
    def explode():
        pytest.fail("SNS must not be contacted when SMS_DRIVER is unset")

    monkeypatch.setattr(user_views, "SnsService", lambda: explode())

    response = client.post(REQUEST_URL, {"mobile": "+919000000004"})

    assert response.status_code == status.HTTP_200_OK
    assert OneTimePassword.objects.filter(mobile="+919000000004").exists()


def test_otp_request_with_sns_driver_uses_stubbed_client_no_live_call(
    client, db, monkeypatch
):
    # a botocore-stubbed SNS client so the publish path cannot reach live AWS
    sns_client = boto3.client(
        "sns",
        region_name="us-east-1",
        aws_access_key_id="stub",
        aws_secret_access_key="stub",
    )
    stubber = Stubber(sns_client)
    stubber.add_response("set_sms_attributes", {})
    stubber.add_response("publish", {"MessageId": "stub-message-id"})
    stubber.activate()

    monkeypatch.setattr(user_views, "SMS_DRIVER", "sns")
    monkeypatch.setattr(user_services.boto3, "client", lambda *a, **k: sns_client)

    try:
        response = client.post(REQUEST_URL, {"mobile": "+919000000005"})
        assert response.status_code == status.HTTP_200_OK
        # both SNS operations were served by the stub — no live call happened
        stubber.assert_no_pending_responses()
    finally:
        stubber.deactivate()
