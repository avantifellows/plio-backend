from rest_framework import permissions


class PlioPermission(permissions.BasePermission):
    """
    Global permission check for plios.
    """

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        if view.action == "duplicate":
            return request.user == obj.created_by

        if view.action == "download_data":
            return request.user == obj.created_by
