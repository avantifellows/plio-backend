from rest_framework import permissions
from users.models import OrganizationUser, Role


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


class OrganizationUserPermission(permissions.BasePermission):
    """
    Permission check for organization-user mapping.
    """

    def has_permission(self, request, view):
        """View-level permissions for organization-user. This determines whether the request can access organization-user instances or not."""
        if request.user.is_superuser:
            return True

        if view.action in ["list", "retrieve"]:
            return True

        organization_user = OrganizationUser.objects.filter(
            organization=request.data["organization"],
            user=request.user.id,
            role__name__in=["org-admin", "super-admin"],
        ).first()

        if not organization_user:
            # user doesn't belong to the queried organization
            # or doesn't have sufficient role within organization
            return False

        requested_role = Role.objects.filter(id=request.data["role"]).first()

        # super-admins can add users with org-admin and org-view roles to their organization
        if organization_user.role.name == "super-admin":
            return requested_role.name in ["org-admin", "org-view"]

        # or-admins can add users with org-view role to their organization
        if organization_user.role.name == "org-admin":
            return requested_role.name == "org-view"

        return False

    def has_object_permission(self, request, view, obj):
        """Object-level permissions for organization-user. This determines whether the request can access an organization-user instance or not."""
        if request.user.is_superuser:
            return True

        # only organization admins are allowed to access organization-user instance
        user_is_organization_admin = OrganizationUser.objects.filter(
            organization=request.data["organization"],
            user=request.user.id,
            role__name="org-admin",
        ).exists()
        return user_is_organization_admin
