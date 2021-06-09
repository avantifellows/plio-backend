from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from rest_framework import status
from oauth2_provider.models import Application
from django.urls import reverse
from users.models import OneTimePassword
from plio.settings import API_APPLICATION_NAME


class BaseTestCase(APITestCase):
    """Base class that sets up generic pre-requisites for all further test classes"""

    def setUp(self):
        self.client = APIClient()

        # User access and refresh tokens require an OAuth Provider application to be set up and use it as a foreign key.
        # As the test database is empty, we create an application instance before running the test cases.
        Application.objects.create(
            name=API_APPLICATION_NAME,
            redirect_uris="",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )


class OtpAuthTestCase(BaseTestCase):
    """Tests the OTP functionality."""

    def setUp(self):
        super().setUp()
        self.user_mobile = "+919876543210"

    def test_guest_can_request_for_otp(self):
        response = self.client.post(
            reverse("request_otp"), {"mobile": self.user_mobile}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        otp_exists = OneTimePassword.objects.filter(mobile=self.user_mobile).exists()
        self.assertTrue(otp_exists)

    def test_invalid_otp_should_fail(self):
        # request otp
        self.client.post(reverse("request_otp"), {"mobile": self.user_mobile})

        # invalid otp
        otp = "000000"
        response = self.client.post(
            reverse("verify_otp"), {"mobile": self.user_mobile, "otp": otp}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_valid_otp_should_pass(self):
        # request otp
        self.client.post(reverse("request_otp"), {"mobile": self.user_mobile})

        # verify valid otp
        otp = OneTimePassword.objects.filter(mobile=self.user_mobile).first()
        response = self.client.post(
            reverse("verify_otp"), {"mobile": self.user_mobile, "otp": otp.otp}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
