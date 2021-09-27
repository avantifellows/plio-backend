from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save, post_delete
from django.core.mail import send_mail
from django.template.loader import render_to_string
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from users.views import send_welcome_sms
from users.models import User, OrganizationUser
from users.serializers import UserSerializer
from plio.cache import invalidate_cache_for_instance, invalidate_cache_for_instances

from plio.settings import (
    DEFAULT_FROM_EMAIL,
)


@receiver(pre_save, sender=User)
def update_user(sender, instance: User, **kwargs):
    if not instance.id:
        # new user is created
        if instance.status == "approved" and instance.mobile:
            # the new user has logged in through phone number
            send_welcome_sms(instance.mobile)
        return

    # existing user is updated
    old_instance = sender.objects.get(id=instance.id)
    if old_instance.status != instance.status:
        # execute this only if the user status has changed
        user_data = UserSerializer(instance).data
        channel_layer = get_channel_layer()
        user_group_name = f"user_{user_data['id']}"
        async_to_sync(channel_layer.group_send)(
            user_group_name, {"type": "send_user", "data": user_data}
        )

        if instance.status == "approved":
            # send an email or an sms if the user has been approved
            if instance.email:
                # user signed up with email
                subject = "Congrats - You're off the Plio waitlist! 🎉"
                recipient_list = [
                    instance.email,
                ]
                html_message = render_to_string("waitlist-approve-email.html")
                send_mail(
                    subject=subject,
                    message=None,
                    from_email=DEFAULT_FROM_EMAIL,
                    recipient_list=recipient_list,
                    html_message=html_message,
                )
            elif instance.mobile:
                # user signed up with mobile
                send_welcome_sms(instance.mobile)


@receiver(post_save, sender=OrganizationUser)
@receiver(post_delete, sender=OrganizationUser)
def update_organization_user(sender, instance: OrganizationUser, **kwargs):
    # execute this if a user is added to/removed from an organization
    user_data = UserSerializer(instance.user).data
    channel_layer = get_channel_layer()
    user_group_name = f"user_{user_data['id']}"
    async_to_sync(channel_layer.group_send)(
        user_group_name, {"type": "send_user", "data": user_data}
    )


@receiver(post_save, sender=User)
@receiver(post_delete, sender=User)
def user_update_cache(sender, instance, created, raw, **kwargs):
    invalidate_cache_for_instance(instance)

    # invalidate cache for plios created by user
    from plio.models import Plio

    plios = Plio.objects.filter(created_by_id=instance.id)
    invalidate_cache_for_instances(plios)


@receiver(post_save, sender=OrganizationUser)
@receiver(post_delete, sender=OrganizationUser)
def organization_user_update_cache(sender, instance, **kwargs):
    invalidate_cache_for_instance(instance.user)
