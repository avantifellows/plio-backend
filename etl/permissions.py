from rest_framework import permissions


class ETLPermissions(permissions.BasePermission):
    """
    Permission check for etl app.
    """

    def has_permission(self, request, view):
        """View-level permissions for etl viewset. This determines whether the request can access etl viewset or not."""
        return request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        """Object-level permissions for etl app. This determines whether the request can access an etl instance or not."""
        return request.user.is_superuser
