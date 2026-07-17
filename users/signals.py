from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete, pre_save
from oauth2_provider.models import Application

from plio.settings import API_APPLICATION_NAME, DEFAULT_OAUTH2_CLIENT_ID
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from users.models import User, OrganizationUser
from users.serializers import UserSerializer
from plio.cache import invalidate_cache_for_instance, invalidate_cache_for_instances

# the cache invalidate receivers must be defined before any other receiver,
# so that the instance data in other receivers is always up to date.


@receiver([post_save, post_delete], sender=User)
def user_update_cache(sender, instance, **kwargs):
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


@receiver(pre_save, sender=Application)
def keep_convert_token_application_secret_plaintext(sender, instance, **kwargs):
    """
    The convert-token application's secret must stay retrievable plaintext:
    drf-social-oauth2 injects the STORED secret into the token exchange, so
    a hashed secret breaks every Google login. users/0022 repairs existing
    rows; this guard covers applications created or edited afterwards (e.g.
    through the Django admin), where django-oauth-toolkit >= 2.4 would
    default hash_client_secret=True and hash on save.
    """
    is_convert_token_app = instance.name == API_APPLICATION_NAME or (
        DEFAULT_OAUTH2_CLIENT_ID and instance.client_id == DEFAULT_OAUTH2_CLIENT_ID
    )
    if is_convert_token_app:
        instance.hash_client_secret = False
