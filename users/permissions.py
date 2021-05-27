from rest_framework import permissions
from users.models import Role


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

        # when listing, a user should only see organization-user mapping for the organizations they have access to.
        # this is handled by get_queryset
        if view.action in ["list", "retrieve", "destroy"]:
            return True

        user_organization_role = request.user.get_role_for_organization(
            request.data["organization"]
        )
        if not user_organization_role or user_organization_role.name not in [
            "org-admin",
            "super-admin",
        ]:
            # user doesn't belong to the queried organization
            # or doesn't have sufficient role within organization
            return False

        if "role" not in request.data:
            return False

        requested_role = Role.objects.filter(id=request.data["role"]).first()

        # super-admins can add users with org-admin and org-view roles to their organization
        if user_organization_role.name == "super-admin":
            return requested_role.name in ["org-admin", "org-view"]

        # or-admins can add users with org-view role to their organization
        if user_organization_role.name == "org-admin":
            return requested_role.name == "org-view"

        return False

    def has_object_permission(self, request, view, obj):
        """Object-level permissions for organization-user. This determines whether the request can access an organization-user instance or not."""
        if request.user.is_superuser:
            return True

        if view.action == "retrieve":
            return True

        if view.action == "destroy":
            organization_id = obj.organization_id
        else:
            organization_id = request.data["organization"]

        user_organization_role = request.user.get_role_for_organization(organization_id)

        # only super-admin and org-admin can access organization_user instance
        if user_organization_role.name not in ["super-admin", "org-admin"]:
            return False

        # super-admins can add users with org-admin and org-view roles to their organization
        if user_organization_role.name == "super-admin":
            return obj.role.name in ["org-admin", "org-view"]

        # org-admins can add users with org-view role to their organization
        if user_organization_role.name == "org-admin":
            return obj.role.name == "org-view"
