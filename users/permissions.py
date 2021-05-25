from rest_framework import permissions


class UserPermission(permissions.BasePermission):
    """
    Global permission check for users.
    """

    def has_permission(self, request, view):
        if view.action in ["list", "create"]:
            # only superuser can list or create users
            return request.user.is_superuser

        return True

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser or request.user == obj
