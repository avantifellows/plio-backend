from plio.tests import BaseTestCase
from organizations.models import Organization
from rest_framework import status
from django.urls import reverse


class OrganizationTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        # seed some organizations
        Organization.objects.create(name="Org 1", shortcode="org-1")
        Organization.objects.create(name="Org 2", shortcode="org-2")

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
