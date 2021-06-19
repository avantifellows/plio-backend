import json
from rest_framework import status
from django.urls import reverse
from users.models import OneTimePassword, Role, OrganizationUser
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

    def test_user_cannot_get_other_user_config(self):
        # get config
        response = self.client.get(f"/api/v1/users/{self.user_2.id}/config/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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

    def test_user_cannot_update_other_user_config(self):
        # get config
        response = self.client.patch(
            f"/api/v1/users/{self.user_2.id}/config/",
            {"config": {"test": True}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_by_access_token_access_token_not_passed(self):
        response = self.client.get(reverse("get-by-access-token"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_by_access_token_access_token_invalid(self):
        response = self.client.get(reverse("get-by-access-token"), {"token": "1234"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_by_access_token_valid_user(self):
        response = self.client.get(
            reverse("get-by-access-token"), {"token": self.access_token.token}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.user.id)


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

        # create another organization
        self.organization_2 = Organization.objects.create(
            name="Org 2", shortcode="org-2"
        )

        # seed some organization users
        self.org_user_1 = OrganizationUser.objects.create(
            organization=self.organization, user=self.user, role=self.org_view_role
        )

        self.org_user_2 = OrganizationUser.objects.create(
            organization=self.organization_2, user=self.user, role=self.org_view_role
        )

    def test_superuser_can_list_all_organization_users(self):
        # make the current user as superuser
        self.user.is_superuser = True
        self.user.save()

        # get organization users
        response = self.client.get(reverse("organization-users-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]["user"], self.user.id)
        self.assertEqual(response.json()[1]["user"], self.user.id)
        self.assertEqual(response.json()[0]["organization"], self.organization.id)
        self.assertEqual(response.json()[1]["organization"], self.organization_2.id)

    def test_normal_user_cannot_list_organization_users(self):
        # get organization users
        response = self.client.get(reverse("organization-users-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)

    def test_org_admin_can_list_only_their_organization_users(self):
        # make user 2 org-admin for org 1
        org_admin_role = Role.objects.filter(name="org-admin").first()
        OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=org_admin_role
        )

        # change user
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer " + self.access_token_2.token,
        )

        # get organization users
        response = self.client.get(reverse("organization-users-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]["user"], self.user.id)
        self.assertEqual(response.json()[0]["organization"], self.organization.id)
        self.assertEqual(response.json()[1]["user"], self.user_2.id)
        self.assertEqual(response.json()[1]["organization"], self.organization.id)

    def test_normal_user_cannot_create_organization_user(self):
        # add organization_user to the organization
        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.user.id,
                "organization": self.organization.id,
                "role": self.org_view_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_create_organization_user(self):
        # make the current user as superuser
        self.user.is_superuser = True
        self.user.save()

        # add organization_user to the organization
        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.user.id,
                "organization": self.organization.id,
                "role": self.org_view_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
