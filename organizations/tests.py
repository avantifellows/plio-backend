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
        self.assertEqual(len(cache.keys(cache_key_name)), 0)

        # make a get request
        self.client.get(reverse("users-detail", kwargs={"pk": self.user.id}))
        # verify cache data exists as we made a GET request for user details
        self.assertEqual(len(cache.keys(cache_key_name)), 1)
        self.assertEqual(len(cache.get(cache_key_name)["organizations"]), 0)

        # associate the current user with the organization
        OrganizationUser.objects.create(
            organization=self.organization_2, user=self.user, role=self.org_admin_role
        )

        # check cache after updating organization user association
        # this time the user should have an organization associated
        self.assertEqual(len(cache.get(cache_key_name)["organizations"]), 1)
        self.assertEqual(
            cache.get(cache_key_name)["organizations"][0]["name"],
            self.organization_2.name,
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
