from django.core.cache import cache


def get_cache_key(model_name, instance):
    return {
        "User": f"user_{instance.pk}",
        "UserMeta": f"user_meta_{instance.pk}",
    }.get(model_name, f"user_{instance.pk}")


def invalidate_cache_for_instance(model_name, instance):
    cache_key = get_cache_key(model_name, instance)
    cache.delete(cache_key)
    # invalidate cache for related fields

    # to_update = cache.update_instance(model_name, instance_pk, instance, version)
    # for related_name, related_pk, related_version in to_update:
    #     invalidate_cache_for_instance(related_name, related_pk, version=related_version)
