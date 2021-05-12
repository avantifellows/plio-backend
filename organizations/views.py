from rest_framework import viewsets
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer


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

    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
