from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from users.models import User, OrganizationUser
from users.serializers import UserSerializer
from plio.cache import invalidate_cache_for_instance, invalidate_cache_for_instances

# the cache invalidate receivers must be defined before any other receiver,
# so that the instance data in other receivers is always up to date.


@receiver([post_save, post_delete], sender=User)
def user_update_cache(sender, instance, created, raw, **kwargs):
    invalidate_cache_for_instance(instance)

    # invalidate cache for plios created by user
    from plio.models import Plio

    plios = Plio.objects.filter(created_by_id=instance.id)
    invalidate_cache_for_instances(plios)


@receiver([post_save, post_delete], sender=OrganizationUser)
def organization_user_update_cache(sender, instance, **kwargs):
    invalidate_cache_for_instance(instance.user)


@receiver([post_save, post_delete], sender=OrganizationUser)
def update_organization_user(sender, instance: OrganizationUser, **kwargs):
    # execute this if a user is added to/removed from an organization
    user_data = UserSerializer(instance.user).data
    channel_layer = get_channel_layer()
    user_group_name = f"user_{user_data['id']}"
    async_to_sync(channel_layer.group_send)(
        user_group_name, {"type": "send_user", "data": user_data}
    )
