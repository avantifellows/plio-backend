from rest_framework import permissions


class OrganizationPermission(permissions.BasePermission):
    """
    Permission check for organizations.
    """

    def has_permission(self, request, view):
        """View-level permissions for organization viewset. This determines whether the request can access organization viewset or not."""
        return True

    def has_object_permission(self, request, view, obj):
        """Object-level permissions for an organization. This determines whether the request can access an organization instance or not."""
        if view.action in ["setting"]:
            return request.user.is_superuser or request.user.is_org_admin(
                organization_id=int(view.kwargs["pk"])
            )
        return request.user.is_superuser
