from rest_framework import permissions


class PlioPermission(permissions.BasePermission):
    """
    Permission check for plios.
    """

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser or request.user == obj.created_by
