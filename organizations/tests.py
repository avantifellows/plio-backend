from rest_framework import status
from django.urls import reverse

# from django.core.cache import cache

from plio.tests import BaseTestCase
from organizations.models import Organization

# from plio.cache import get_cache_key
# from users.models import OrganizationUser


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

    # def test_updating_organization_recreates_user_instance_cache(self):
    #     # make a get request
    #     user_details = self.client.get(
    #         reverse("users-detail", kwargs={"pk": self.user.id})
    #     )
    #     self.assertEqual(len(user_details["organizations"]), 0)

    #     # create a new organization
    #     # print('creating organization')
    #     # organization = Organization.objects.create(name="Org 3", shortcode="org-3")
    #     # print('created organization', organization)

    #     # associate the current user with the organization
    #     OrganizationUser.objects.create(
    #         organization=self.organization_2, user=self.user, role=self.org_admin_role
    #     )
    #     print("user association created organization")

    #     # verify cache data doesn't exist
    #     cache_key_name = get_cache_key(self.user)

    #     # verify cache data exists
    #     self.assertEqual(len(cache.keys(cache_key_name)), 1)

    #     # make an update
    #     org_name = "Org New Name"
    #     self.client.patch(
    #         reverse("organizations-detail", kwargs={"pk": organization.id}),
    #         {"name": org_name},
    #     )

    #     # verify cache data exist with the updated value
    #     self.assertEqual(len(cache.keys(cache_key_name)), 1)
    #     self.assertEqual(
    #         cache.get(cache_key_name)["organizations"][0]["name"], org_name
    #     )
