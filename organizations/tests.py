from rest_framework import status
from django.urls import reverse

from django.core.cache import cache

from plio.tests import BaseTestCase
from plio.cache import get_cache_key
from organizations.models import Organization
from users.models import OrganizationUser


class OrganizationTestCase(BaseTestCase):
    @classmethod
    def setUpTestData(self):
        super().setUpTestData()
        # seed some organizations
        self.organization_1 = Organization.objects.create(
            name="Org 1", shortcode="org-1"
        )
        self.organization_2 = Organization.objects.create(
            name="Org 2", shortcode="org-2"
        )

    def test_guest_cannot_list_organization(self):
        # unset the access token so that API requests go as unauthenticated user
        self.client.credentials()
        # Make a request without access token
        response = self.client.get(reverse("organizations-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guest_cannot_list_organization_random_token(self):
        # Random token should give 401_unauthorized status
        invalid_token = "abcd"
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + invalid_token)

        response = self.client.get(reverse("organizations-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_superuser_cannot_list_organizations(self):
        """A non-superuser should not be able to list organizations"""
        # get organizations
        response = self.client.get(reverse("organizations-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_list_organizations(self):
        """A superuser should be able to list organizations"""
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(reverse("organizations-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_updating_organization_recreates_user_instance_cache(self):
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

        # verify cache data doesn't exist by default
        cache_key_name = get_cache_key(self.user)

        # make a get request
        self.client.get(reverse("users-detail", kwargs={"pk": self.user.id}))

        # associate the current user with the organization
        OrganizationUser.objects.create(
            organization=self.organization_2, user=self.user, role=self.org_admin_role
        )

        # make an update to the organization name. Only plio superadmin can do it!
        org_new_name = "Org New Name"
        superadmin_client.patch(
            reverse("organizations-detail", kwargs={"pk": self.organization_2.id}),
            {"name": org_new_name},
        )

        # user cache should be deleted after organization update
        self.assertEqual(len(cache.keys(cache_key_name)), 0)

        # request user again so that we can check if the cache is updated
        self.client.get(reverse("users-detail", kwargs={"pk": self.user.id}))

        # verify cache data has now the updated value
        self.assertEqual(
            cache.get(cache_key_name)["organizations"][0]["name"], org_new_name
        )

    def test_settings_support_only_patch_method(self):
        # some dummy settings
        dummy_settings = {"setting_name": "setting_value"}

        # make the current user a superuser
        self.user.is_superuser = True
        self.user.save()

        # try to list the settings
        response = self.client.get(
            f"/api/v1/organizations/{self.organization_1.id}/setting/"
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # try a POST request to settings
        response = self.client.post(
            f"/api/v1/organizations/{self.organization_1.id}/setting/", dummy_settings
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # try a PUT request to settings
        response = self.client.put(
            f"/api/v1/organizations/{self.organization_1.id}/setting/", dummy_settings
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # try a PATCH request to settings
        response = self.client.patch(
            f"/api/v1/organizations/{self.organization_1.id}/setting/", dummy_settings
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Organization.objects.filter(id=self.organization_1.id)
            .first()
            .config["settings"],
            dummy_settings,
        )

    def test_superuser_can_update_any_org_settings(self):
        # some dummy settings
        dummy_settings = {"setting_name": "setting_value"}

        # turn the current user into a superuser
        self.user.is_superuser = True
        self.user.save()

        # try updating settings of org 1
        response = self.client.put(
            f"/api/v1/organizations/{self.organization_1.id}/setting/", dummy_settings
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Organization.objects.filter(id=self.organization_1.id)
            .first()
            .config["settings"],
            dummy_settings,
        )

        # try updating settings of org 2
        response = self.client.put(
            f"/api/v1/organizations/{self.organization_2.id}/setting/", dummy_settings
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Organization.objects.filter(id=self.organization_2.id)
            .first()
            .config["settings"],
            dummy_settings,
        )

    def test_org_admin_can_update_own_org_settings_only(self):
        """Only an admin of an org can update the org's settings"""
        from rest_framework.test import APIClient
        from users.models import User
        from plio.tests import get_new_access_token

        # some dummy settings
        dummy_settings = {"setting_name": "setting_value"}

        # user should NOT be able to update org 1 settings as
        # the user is not an org admin
        response = self.client.put(
            f"/api/v1/organizations/{self.organization_1.id}/setting/", dummy_settings
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # create a new super user
        superuser_client = APIClient()
        superuser = User.objects.create(mobile="+919988776655", is_superuser=True)
        superuser_access_token = get_new_access_token(superuser, self.application)
        superuser_client.credentials(
            HTTP_AUTHORIZATION="Bearer " + superuser_access_token.token
        )

        # Make the current user org admin for organization 1 (using the created super user above)
        superuser_client.post(
            reverse("organization-users-list"),
            {
                "user": self.user.id,
                "organization": self.organization_1.id,
                "role": self.org_admin_role.id,
            },
        )

        # user should be able to update org 1 settings
        response = self.client.put(
            f"/api/v1/organizations/{self.organization_1.id}/setting/", dummy_settings
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Organization.objects.filter(id=self.organization_1.id)
            .first()
            .config["settings"],
            dummy_settings,
        )

        # but the user still should NOT be able to update settings for org 2
        response = self.client.put(
            f"/api/v1/organizations/{self.organization_2.id}/setting/", dummy_settings
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            Organization.objects.filter(id=self.organization_2.id).first().config, None
        )
