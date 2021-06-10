from rest_framework import status
from django.urls import reverse
from users.models import OneTimePassword
from plio.tests import BaseTestCase


class OtpAuthTestCase(BaseTestCase):
    """Tests the OTP functionality."""

    def setUp(self):
        super().setUp()
        # unset client credentials token so that the subsequent API calls goes as guest
        self.client.credentials()
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


class UserMetaCRUDTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_for_user_meta(self):
        # write API calls here
        self.assertTrue(True)


class RoleCRUDTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_for_role(self):
        # write API calls here
        self.assertTrue(True)


class OrganizationUserCRUDTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_for_organization_user(self):
        # write API calls here
        self.assertTrue(True)
