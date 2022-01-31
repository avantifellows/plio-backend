from rest_framework import viewsets, status
from organizations.models import Organization
from organizations.serializers import OrganizationSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
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

    permission_classes = [IsAuthenticated, OrganizationPermission]
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

    @action(
        detail=True,
        permission_classes=[IsAuthenticated, OrganizationPermission],
        methods=["patch"],
    )
    def setting(self, request, pk):
        """Updates an org's settings"""
        org = self.get_object()
        org.config = org.config if org.config is not None else {}
        org.config["settings"] = self.request.data
        org.save()
        return Response(
            self.get_serializer(org).data["config"]
        )
