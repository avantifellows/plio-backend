from plio.tests import BaseTestCase
from organizations.models import Organization
from rest_framework import status
from django.urls import reverse


class OrganizationCRUDTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        # seed some organizations
        Organization.objects.create(name="Org 1", shortcode="org-1")
        Organization.objects.create(name="Org 2", shortcode="org-2")

    def test_normal_user_list_organizations(self):
        """A non-superuser should not be able to list organizations"""
        # get organizations
        response = self.client.get(reverse("organization-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
