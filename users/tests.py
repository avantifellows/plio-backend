import json
from rest_framework import status
from django.urls import reverse
from django.core.cache import cache

from oauth2_provider.models import AccessToken, RefreshToken
from users.models import User
from users.models import OneTimePassword, OrganizationUser
from organizations.models import Organization
from plio.tests import BaseTestCase
from plio.cache import get_cache_key


class OtpAuthTestCase(BaseTestCase):
    """Tests the OTP functionality."""

    def setUp(self):
        super().setUp()
        # unset client credentials token so that the subsequent API calls goes as guest
        self.client.credentials()

    def test_requesting_otp_fails_when_mobile_not_passed(self):
        response = self.client.post(reverse("request-otp"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Mobile Not Provided")

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
        response = self.client.post(
            reverse("generate_external_auth_access_token"), payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "api_key not provided.")

        payload = {"api_key": "api_key_1"}
        response = self.client.post(
            reverse("generate_external_auth_access_token"), payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "unique_id not provided.")

    def test_guest_can_authenticate_using_third_party(self):
        # unset client credentials token so that the subsequent API calls goes as guest
        self.client.credentials()

        # some valid dummy third party auth details
        third_party_auth_details = {
            "unique_id": "test_id",
            "api_key": self.organization.api_key,
        }

        response = self.client.post(
            reverse("generate_external_auth_access_token"), third_party_auth_details
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
            auth_org=self.organization,
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
            reverse("generate_external_auth_access_token"), third_party_auth_details
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
        user = User.objects.create(unique_id="test_id", auth_org=self.organization)
        total_users = User.objects.count()

        # authenticate the same user again via third party auth
        third_party_auth_details = {
            "unique_id": "test_id",
            "api_key": self.organization.api_key,
        }
        response = self.client.post(
            reverse("generate_external_auth_access_token"), third_party_auth_details
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
            reverse("generate_external_auth_access_token"), third_party_auth_details
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserTestCase(BaseTestCase):
    def test_user_manager_create_user_with_email(self):
        test_email = "test@gmail.com"
        user = User.objects.create_user(email=test_email)

        self.assertEqual(user.email, test_email)

    def test_general_user_cannot_list_users(self):
        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_list_users(self):
        # make self.user superuser
        self.user.is_superuser = True
        self.user.save()

        response = self.client.get("/api/v1/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_property_name(self):
        test_first_name = "first"
        test_last_name = "last"
        self.user.first_name = test_first_name
        self.user.last_name = test_last_name
        self.user.save()

        self.assertEqual(self.user.name, f"{test_first_name} {test_last_name}")

    def test_user_string_representation(self):
        test_first_name = "first"
        test_last_name = "last"
        self.user.first_name = test_first_name
        self.user.last_name = test_last_name
        self.user.save()

        self.assertEqual(
            str(self.user), f"{self.user.id}: {test_first_name} {test_last_name}"
        )

    def test_user_role_not_part_of_org(self):
        """Tests get_role_for_organization for user who is not part of the given org"""
        self.assertIsNone(self.user.get_role_for_organization(self.organization.id))

    def test_create_superuser_no_email(self):
        with self.assertRaises(TypeError):
            User.objects.create_superuser()

    def test_create_superuser_empty_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="")

        with self.assertRaises(ValueError):
            User.objects.create_superuser(email=None)

    def test_create_superuser_no_password(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="test@gmail.com")

    def test_create_superuser_valid_args(self):
        superuser = User.objects.create_superuser(
            email="test@gmail.com", password="test123"
        )
        self.assertTrue(superuser.is_superuser)

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

    def test_updating_user_recreates_instance_cache(self):
        # verify cache data doesn't exist
        cache_key_name = get_cache_key(self.user)
        self.assertEqual(len(cache.keys(cache_key_name)), 0)

        # make a get request
        self.client.get(reverse("users-detail", kwargs={"pk": self.user.id}))

        # verify cache data exists
        self.assertEqual(len(cache.keys(cache_key_name)), 1)

        # make an update
        first_name = "John"
        self.client.patch(
            reverse("users-detail", kwargs={"pk": self.user.id}),
            {"first_name": first_name},
        )

        # verify cache data exist with the updated value
        self.assertEqual(len(cache.keys(cache_key_name)), 1)
        self.assertEqual(cache.get(cache_key_name)["first_name"], first_name)


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
        OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.org_admin_role
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

    def test_cannot_create_org_user_if_role_not_present(self):
        # try adding organization_user to the organization
        # without sending role in the param
        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.user.id,
                "organization": self.organization.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_org_superadmin_cannot_create_another_superadmin(self):
        self.org_user_1.role = self.super_admin_role
        self.org_user_1.save()

        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.super_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_org_superadmin_can_create_orgadmin_orgview_user(self):
        self.org_user_1.role = self.super_admin_role
        self.org_user_1.save()

        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_view_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_orgadmin_cannot_create_superadmin_orgadmin(self):
        self.org_user_1.role = self.org_admin_role
        self.org_user_1.save()

        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.super_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_orgadmin_can_create_orgview_user(self):
        self.org_user_1.role = self.org_admin_role
        self.org_user_1.save()

        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_view_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_orgview_user_cannot_create_user_to_org(self):
        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_view_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.super_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(
            reverse("organization-users-list"),
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_update_orguser(self):
        # make self.user superuser
        self.user.is_superuser = True
        self.user.save()

        # create user_2 as new org user
        org_user = OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.org_view_role
        )
        response = self.client.put(
            f"/api/v1/organization-users/{org_user.id}/",
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superadmin_cannot_update_superadmin(self):
        self.org_user_1.role = self.super_admin_role
        self.org_user_1.save()

        # create user_2 as new org superadmin
        org_user = OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.super_admin_role
        )
        response = self.client.put(
            f"/api/v1/organization-users/{org_user.id}/",
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.put(
            f"/api/v1/organization-users/{org_user.id}/",
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_view_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superadmin_can_update_orgadmin_orgview_user(self):
        self.org_user_1.role = self.super_admin_role
        self.org_user_1.save()

        # create user_2 as new orgview user
        org_user = OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.org_view_role
        )
        response = self.client.put(
            f"/api/v1/organization-users/{org_user.id}/",
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # create user_2 as new orgadmin user
        org_user = OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.org_admin_role
        )
        response = self.client.put(
            f"/api/v1/organization-users/{org_user.id}/",
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_view_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superadmin_cannot_update_orgadmin_orgview_to_superadmin(self):
        self.org_user_1.role = self.super_admin_role
        self.org_user_1.save()

        # create user_2 as new orgview user
        org_user = OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.org_view_role
        )
        response = self.client.put(
            f"/api/v1/organization-users/{org_user.id}/",
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.super_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # create user_2 as new orgadmin user
        org_user = OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.org_admin_role
        )
        response = self.client.put(
            f"/api/v1/organization-users/{org_user.id}/",
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.super_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_orgadmin_cannot_update_superadmin_orgadmin(self):
        self.org_user_1.role = self.org_admin_role
        self.org_user_1.save()

        # create user_2 as new org superadmin
        org_user = OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.super_admin_role
        )
        response = self.client.put(
            f"/api/v1/organization-users/{org_user.id}/",
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.put(
            f"/api/v1/organization-users/{org_user.id}/",
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_view_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # create user_2 as new orgadmin
        org_user = OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.org_admin_role
        )
        response = self.client.put(
            f"/api/v1/organization-users/{org_user.id}/",
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.super_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.put(
            f"/api/v1/organization-users/{org_user.id}/",
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_view_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_orgadmin_cannot_update_orgview_user(self):
        self.org_user_1.role = self.org_admin_role
        self.org_user_1.save()

        # create user_2 as new orgview user
        org_user = OrganizationUser.objects.create(
            organization=self.organization, user=self.user_2, role=self.org_view_role
        )
        response = self.client.put(
            f"/api/v1/organization-users/{org_user.id}/",
            {
                "user": self.user_2.id,
                "organization": self.organization.id,
                "role": self.org_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_orgview_user_cannot_update_self(self):
        self.org_user_1.role = self.org_view_role
        self.org_user_1.save()

        response = self.client.put(
            f"/api/v1/organization-users/{self.org_user_1.id}/",
            {
                "user": self.user.id,
                "organization": self.organization.id,
                "role": self.org_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.put(
            f"/api/v1/organization-users/{self.org_user_1.id}/",
            {
                "user": self.user.id,
                "organization": self.organization.id,
                "role": self.super_admin_role.id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_updating_organization_user_recreates_user_instance_cache(self):
        from users.models import User
        from rest_framework.test import APIClient
        from plio.tests import get_new_access_token

        superadmin_client = APIClient()
        superadmin_user = User.objects.create(mobile="+919988776655", is_superuser=True)
        superadmin_access_token = get_new_access_token(
            superadmin_user, self.application
        )
        superadmin_client.credentials(
            HTTP_AUTHORIZATION="Bearer " + superadmin_access_token.token
        )

        # create a new user
        user = User.objects.create(mobile="+919977553311")

        # verify cache data doesn't exist by default
        cache_key_name = get_cache_key(user)
        self.assertEqual(len(cache.keys(cache_key_name)), 0)

        # make a get request
        superadmin_client.get(reverse("users-detail", kwargs={"pk": user.id}))
        # verify cache data exists as we made a GET request for user details
        self.assertEqual(len(cache.keys(cache_key_name)), 1)
        self.assertEqual(len(cache.get(cache_key_name)["organizations"]), 0)

        # associate the current user with the organization
        OrganizationUser.objects.create(
            organization=self.organization_2, user=user, role=self.org_admin_role
        )

        # check cache after updating organization user association
        # this time the user should have an organization associated
        self.assertEqual(len(cache.get(cache_key_name)["organizations"]), 1)
        self.assertEqual(
            cache.get(cache_key_name)["organizations"][0]["name"],
            self.organization_2.name,
        )
