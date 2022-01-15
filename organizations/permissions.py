from rest_framework import permissions


class OrganizationPermission(permissions.BasePermission):
    """
    Permission check for organizations.
    """

    def has_permission(self, request, view):
        """View-level permissions for organization. This determines whether the request can access organization instances or not."""
        if view.action == "update":
            org_to_update = int(view.kwargs["pk"])
            return request.user.is_superuser or request.user.is_org_admin(
                organization_id=org_to_update
            )
        return request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        """Object-level permissions for an organization. This determines whether the request can access an organization instance or not."""
        if view.action == "update":
            org_to_update = int(view.kwargs["pk"])
            return request.user.is_superuser or request.user.is_org_admin(
                organization_id=org_to_update
            )
        return request.user.is_superuser
