from rest_framework import viewsets
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from organizations.permissions import OrganizationPermission


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    Organization ViewSet description

    list: List all organizations
    retrieve: Retrieve an organization
    update: Update an organization
    create: Create an organization
    partial_update: Patch an organization
    destroy: Soft delete an organization
    """

    permission_classes = [OrganizationPermission]
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
