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

        has_org_admin_access, user_organization_role = request.user.is_user_org_admin(
            organization_id=request.data["organization"], return_role=True
        )

        if not has_org_admin_access:
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

        # allow anyone to retrieve the instance
        if view.action == "retrieve":
            return True

        if view.action == "destroy":
            # When deleting an organization-user, we will only send the primary key.
            # So to determine if logged-in user is authorized to perform action,
            # we need to pick org id from object
            organization_id = obj.organization_id
        else:
            # When updating an organization user, we will also send a new org id.
            # So to determine if logged-in user is authorized to perform action,
            # we need to pick org id from the request (which is the updated
            # org id for that organization-user)
            organization_id = request.data["organization"]

        user_organization_role = request.user.get_role_for_organization(organization_id)

        # super-admins can add users with org-admin and org-view roles to their organization
        if user_organization_role.name == "super-admin":
            return obj.role.name in ["org-admin", "org-view"]

        # org-admins can add users with org-view role to their organization
        if user_organization_role.name == "org-admin":
            return obj.role.name == "org-view"
