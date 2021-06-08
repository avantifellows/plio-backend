from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from users.models import OneTimePassword, User
from plio.settings import API_APPLICATION_NAME
from oauth2_provider.models import Application
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status


class BaseTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        call_command("pliosuperuser")
        self.super_user = User.objects.first()
        Application.objects.create(
            name=API_APPLICATION_NAME,
            redirect_uris="",
            user=self.super_user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        )


class UserAuthenticationTestCase(BaseTestCase):
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

    def test_guest_can_verify_otp(self):
        # request otp
        self.client.post(reverse("request_otp"), {"mobile": self.user_mobile})

        # fetch otp
        otp = OneTimePassword.objects.filter(mobile=self.user_mobile).first()
        response = self.client.post(
            reverse("verify_otp"), {"mobile": self.user_mobile, "otp": otp.otp}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
