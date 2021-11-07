from rest_framework import permissions
from organizations.middleware import OrganizationTenantMiddleware
from plio.settings import DEFAULT_TENANT_SHORTCODE
from plio.models import Plio, Item, Question
from users.models import OrganizationUser


class PlioPermission(permissions.BasePermission):
    """
    Permission check for plios.
    """

    def has_permission(self, request, view):
        """View-level permissions for plio. This determines whether the request can access plio instances or not."""
        return True

    def has_object_permission(self, request, view, obj):
        """Object-level permissions for plio/item/question. This determines whether the request can access a plio/item/question instance or not."""
        if request.user.is_superuser:
            return True

        # if the requested object is an Item or Question, filter the Plio record that it belongs to
        # and use the permission logic on that Plio instance
        if isinstance(obj, Question):
            obj = Plio.objects.filter(id=obj.item.plio.id).first()
        elif isinstance(obj, Item):
            obj = Plio.objects.filter(id=obj.plio.id).first()

        organization_shortcode = (
            OrganizationTenantMiddleware.get_organization_shortcode(request)
        )
        if organization_shortcode == DEFAULT_TENANT_SHORTCODE:
            # this is the user's personal workspace in the public DB schema
            # only plios created by the user can be accessed
            return request.user == obj.created_by

        # checking if user is a member of the organization
        user_belongs_to_organization = OrganizationUser.objects.filter(
            organization__shortcode=organization_shortcode,
            user=request.user.id,
        ).exists()

        if user_belongs_to_organization and obj.is_public:
            return True

        # user doesn't belong to organization or plio isn't public
        return request.user == obj.created_by
