from rest_framework import permissions


class OrganizationPermission(permissions.BasePermission):
    """
    Global permission check for organizations.
    """

    def has_permission(self, request, view):
        return request.user.is_superuser
