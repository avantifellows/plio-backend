from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from plio.cache import invalidate_cache_for_instances
from organizations.models import Organization


@receiver([post_save, post_delete], sender=Organization)
def organization_update_cache(sender, instance, created, raw, **kwargs):
    # invalidate cache for users belonging to organization
    from users.models import User

    users = User.objects.filter(organizations__id=instance.id)
    invalidate_cache_for_instances(users)
