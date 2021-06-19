import json
from rest_framework import status
from django.urls import reverse
from users.models import OneTimePassword, User, Role
from plio.tests import BaseTestCase
from organizations.models import Organization


class OtpAuthTestCase(BaseTestCase):
    """Tests the OTP functionality."""

    def setUp(self):
        super().setUp()
        # unset client credentials token so that the subsequent API calls goes as guest
        self.client.credentials()

    def test_guest_can_request_for_otp(self):
        response = self.client.post(
            reverse("request-otp"), {"mobile": self.user.mobile}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        otp_exists = OneTimePassword.objects.filter(mobile=self.user.mobile).exists()
        self.assertTrue(otp_exists)

    def test_invalid_otp_should_fail(self):
        # request otp
        self.client.post(reverse("request-otp"), {"mobile": self.user.mobile})

        # invalid otp
        otp = "000000"
        response = self.client.post(
            reverse("verify-otp"), {"mobile": self.user.mobile, "otp": otp}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_valid_otp_should_pass(self):
        # request otp
        self.client.post(reverse("request-otp"), {"mobile": self.user.mobile})

        # verify valid otp
        otp = OneTimePassword.objects.filter(mobile=self.user.mobile).first()
        response = self.client.post(
            reverse("verify-otp"), {"mobile": self.user.mobile, "otp": otp.otp}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_valid_otp_should_pass_new_user(self):
        # new user
        new_user_mobile = "+919988776654"

        # request otp
        self.client.post(reverse("request-otp"), {"mobile": new_user_mobile})

        # verify valid otp
        otp = OneTimePassword.objects.filter(mobile=new_user_mobile).first()
        response = self.client.post(
            reverse("verify-otp"), {"mobile": new_user_mobile, "otp": otp.otp}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserTestCase(BaseTestCase):
    def test_get_config(self):
        config = {"test": True}
        # set config
        self.user.config = config
        self.user.save()

        # get config
        response = self.client.get(f"/api/v1/users/{self.user.id}/config/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), config)

    def test_update_config_no_config_provided(self):
        # update config
        response = self.client.patch(f"/api/v1/users/{self.user.id}/config/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_config_extra_params(self):
        # update config
        response = self.client.patch(
            f"/api/v1/users/{self.user.id}/config/",
            {"config": {}, "extra_param": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content)["detail"],
            "extra keys apart from config are not allowed",
        )

    def test_update_config(self):
        # update config
        config = {"test": True}
        response = self.client.patch(
            f"/api/v1/users/{self.user.id}/config/",
            {"config": config},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # get the config to see if it is updated
        response = self.client.get(f"/api/v1/users/{self.user.id}/config/")

        self.assertEqual(
            response.json(),
            config,
        )

    # one user should not be able to get config of another user
    # one user should not be able to update config of another user


class UserMetaTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_for_user_meta(self):
        # write API calls here
        self.assertTrue(True)


class RoleTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_for_role(self):
        # write API calls here
        self.assertTrue(True)


class OrganizationUserTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        # set up an organization
        self.organization = Organization.objects.create(name="Org 1", shortcode="org-1")
        # set up a user that's supposed to be in the organization
        self.organization_user = User.objects.create(mobile="+919988776655")

    def test_normal_user_cannot_create_organization_user(self):
        # get org-view role
        role_org_view = Role.objects.filter(name="org-view").first()
        # add organization_user to the organization
        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.organization_user.id,
                "organization": self.organization.id,
                "role": role_org_view.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_create_organization_user(self):
        # make the current user as superuser
        self.user.is_superuser = True
        self.user.save()

        # get org-view role
        role_org_view = Role.objects.filter(name="org-view").first()
        # add organization_user to the organization
        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.organization_user.id,
                "organization": self.organization.id,
                "role": role_org_view.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
