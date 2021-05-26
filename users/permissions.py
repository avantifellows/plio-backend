from rest_framework import permissions


class UserPermission(permissions.BasePermission):
    """
    Permission check for users.
    """

    def has_permission(self, request, view):
        """View-level permissions for user. This determines whether the request can access user instances or not."""
        if view.action in ["list", "create"]:
            # only superuser can list or create users
            return request.user.is_superuser

        return True

    def has_object_permission(self, request, view, obj):
        """Object-level permissions for user. This determines whether the request can access a user instance or not."""
        return request.user.is_superuser or request.user == obj
