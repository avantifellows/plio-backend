from rest_framework import permissions


class OrganizationPermission(permissions.BasePermission):
    """
    Permission check for organizations.
    """

    def has_permission(self, request, view):
        """View-level permissions for organization. This determines whether the request can access organization instances or not."""
        return request.user.is_superuser
