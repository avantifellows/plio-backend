from django.core.cache import cache


def get_cache_key(instance):
    """Calculates the cache key for an instance"""
    instance_class = instance.__class__.__name__
    return {
        "Video": f"video_{instance.pk}",
        "Plio": f"plio_{instance.pk}",
        "Session": f"session_{instance.pk}",
        "User": f"user_{instance.pk}",
        "UserMeta": f"user_meta_{instance.pk}",
    }.get(instance_class, None)


def invalidate_cache_for_instance(instance):
    """Deletes cache for a particular instance"""
    cache_key = get_cache_key(instance)
    if cache_key:
        cache.delete(cache_key)


def get_cache_keys(instances):
    """Calculates cache keys for a list of instances"""
    keys = []
    for instance in instances:
        keys.append(get_cache_key(instance))
    return keys


def invalidate_cache_for_instances(instances):
    """Deletes cache for a list of instances"""
    cache_keys = get_cache_keys(instances)
    cache.delete_many(cache_keys)
