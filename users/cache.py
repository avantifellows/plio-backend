from django.contrib.auth import get_user_model
from drf_cached_instances.cache import BaseCache

# from organizations.models import Organization

User = get_user_model()


class UserCache(BaseCache):

    """Cache for users application."""

    def user_default_serializer(self, obj):
        """Convert a User to a cached instance representation."""
        print("starting here in UserCache")
        if not obj:
            return None
        self.user_default_add_related_pks(obj)
        print("hello there!")
        print(obj)
        print(obj.email)
        print(obj.organizations)
        print(obj._organizations_pks)
        return dict(
            (
                ("id", obj.id),
                self.field_to_json("DateTime", "date_joined", obj.date_joined),
                self.field_to_json("DateTime", "last_login", obj.last_login),
                ("is_superuser", obj.is_superuser),
                ("first_name", obj.first_name),
                ("last_name", obj.last_name),
                ("is_staff", obj.is_staff),
                ("is_staff", obj.is_staff),
                ("is_active", obj.is_active),
                ("email", obj.email),
                ("mobile", obj.mobile),
                # ('avatar_url', obj.avatar_url),
                ("config", obj.config),
                self.field_to_json("DateTime", "created_at", obj.created_at),
                self.field_to_json("DateTime", "updated_at", obj.updated_at),
                # self.field_pklist_to_json(Organization, obj._organizations_pks),
                # ("organizations", OrganizationUser.objects.get(user=user)),
                ("status", obj.status),
                ("unique_id", obj.unique_id),
                ("auth_org", obj.auth_org),
            )
        )

    def user_default_loader(self, pk):
        """Load a User from the database."""
        try:
            obj = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None
        else:
            self.user_default_add_related_pks(obj)
            return obj

    def user_default_add_related_pks(self, obj):
        """Add related primary keys to a user instance."""
        if not hasattr(obj, "_organizations_pks"):
            obj._organizations_pks = list(
                obj.organizations.values_list("pk", flat=True)
            )

    def user_default_invalidator(self, obj):
        """Invalidate cached items when the User changes."""
        return []
