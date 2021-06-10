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

    def test_non_superuser_cannot_list_organizations(self):
        """A non-superuser should not be able to list organizations"""
        # get organizations
        response = self.client.get(reverse("organizations-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
