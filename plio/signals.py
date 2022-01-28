from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from plio.cache import invalidate_cache_for_instance, invalidate_cache_for_instances
from plio.models import Video, Plio, Item, Question


@receiver([post_save, post_delete], sender=Plio)
def plio_update_cache(sender, instance, **kwargs):
    invalidate_cache_for_instance(instance)


@receiver([post_save, post_delete], sender=Video)
def video_update_cache(sender, instance, **kwargs):
    # fetch all plio with video id
    plios = Plio.objects.filter(video_id=instance.id)
    # invalidate saved cache for the plios
    invalidate_cache_for_instances(plios)


@receiver([post_save, post_delete], sender=Item)
def item_update_cache(sender, instance, **kwargs):
    # invalidate saved cache for the plio
    invalidate_cache_for_instance(instance.plio)


@receiver([post_save, post_delete], sender=Question)
def question_update_cache(sender, instance, **kwargs):
    # invalidate saved cache for the plio
    invalidate_cache_for_instance(instance.item.plio)


@receiver([post_save], sender=Question)
def delete_linked_image_on_question_deletion(sender, instance, **kwargs):
    # check if any image is linked to the instance
    if instance.deleted is not None and instance.image is not None:
        # delete that image as well
        instance.image.delete()
