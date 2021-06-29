import json
from rest_framework import status
from django.urls import reverse

from oauth2_provider.models import AccessToken, RefreshToken
from users.models import User
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


class ThirdPartyAuthTestCase(BaseTestCase):
    """Tests the third party auth functionality"""

    def setUp(self):
        super().setUp()

    def test_cannot_authenticate_without_all_required_keys(self):
        # not sending all the required auth keys
        payload = {"unique_id": "test_id"}
        response = self.client.post(reverse("convert_api_key_to_token"), payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "api_key not provided.")

    def test_guest_can_authenticate_using_third_party(self):
        # unset client credentials token so that the subsequent API calls goes as guest
        self.client.credentials()

        # some valid dummy third party auth details
        third_party_auth_details = {
            "unique_id": "test_id",
            "api_key": self.organization.api_key,
        }

        response = self.client.post(
            reverse("convert_api_key_to_token"), third_party_auth_details
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        access_token_exists = AccessToken.objects.filter(
            token=response.data["access_token"]
        ).exists()
        refresh_token_exists = RefreshToken.objects.filter(
            token=response.data["refresh_token"]
        ).exists()
        user_created = User.objects.filter(
            unique_id=third_party_auth_details["unique_id"],
            org=self.organization,
        ).exists()
        self.assertTrue(access_token_exists)
        self.assertTrue(refresh_token_exists)
        self.assertTrue(user_created)

    def test_third_party_auth_changes_current_logged_in_user(self):
        # retrieve the currently logged in user from client's credentials
        current_access_token = self.client._credentials["HTTP_AUTHORIZATION"].split(
            " "
        )[1]
        current_logged_in_user = (
            AccessToken.objects.filter(token=current_access_token).first().user_id
        )

        # login a new user via third party authentication
        third_party_auth_details = {
            "unique_id": "test_id",
            "api_key": self.organization.api_key,
        }
        response = self.client.post(
            reverse("convert_api_key_to_token"), third_party_auth_details
        )
        # verify that the user for which the new access token is generated, is different than the
        # originally logged in user
        new_access_token = response.data["access_token"]
        new_logged_in_user = (
            AccessToken.objects.filter(token=new_access_token).first().user_id
        )
        self.assertNotEqual(current_logged_in_user, new_logged_in_user)

    def test_existing_third_party_user_can_authenticate_again(self):
        # create a third party user
        user = User.objects.create(unique_id="test_id", org=self.organization)
        total_users = User.objects.count()

        # authenticate the same user again via third party auth
        third_party_auth_details = {
            "unique_id": "test_id",
            "api_key": self.organization.api_key,
        }
        response = self.client.post(
            reverse("convert_api_key_to_token"), third_party_auth_details
        )

        # the request should go through, the generated access_token should be for
        # the defined user earlier, and no new user should've been created
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            AccessToken.objects.filter(token=response.data["access_token"])
            .first()
            .user_id,
            user.id,
        )
        self.assertEqual(total_users, User.objects.count())

    def test_unapproved_api_key_not_allowed(self):
        # try authenticating with an api_key that doesn't exist
        third_party_auth_details = {"unique_id": "test_id", "api_key": "dummy_api_key"}
        response = self.client.post(
            reverse("convert_api_key_to_token"), third_party_auth_details
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


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
        """Updating config without passing the config to use should fail"""
        # update config
        response = self.client.patch(f"/api/v1/users/{self.user.id}/config/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_config_extra_params(self):
        """Passing params other than config while updating config should fail"""
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

    def test_get_analytics_app_access_token(self):
        response = self.client.post(reverse("get-analytics-token"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.json())


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
    @classmethod
    def setUpTestData(self):
        super().setUpTestData()
        # create another organization
        self.organization_2 = Organization.objects.create(
            name="Org 2", shortcode="org-2"
        )

    def setUp(self):
        super().setUp()
        # seed some organization users
        self.org_user_1 = OrganizationUser.objects.create(
            organization=self.organization, user=self.user, role=self.org_view_role
        )

        self.org_user_2 = OrganizationUser.objects.create(
            organization=self.organization_2, user=self.user, role=self.org_view_role
        )

    def test_superuser_can_list_all_org_users(self):
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

    def test_normal_user_only_sees_empty_list_of_org_users(self):
        # get organization users
        response = self.client.get(reverse("organization-users-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)

    def test_org_admin_can_list_only_their_org_users(self):
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

    def test_normal_user_cannot_create_org_user(self):
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

    def test_superuser_can_create_org_user(self):
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
