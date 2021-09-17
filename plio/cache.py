from django.core.cache import cache
from django.db import connection


def get_cache_key(instance):
    """Calculates the cache key for an instance based on selected schema and """
    schema_name = connection.schema_name
    instance_class = instance.__class__.__name__

    # the following list of key-value pairs returns the value if key matches instance_class, otherwise None
    return {
        # instances that are tenant specific
        "Video": f"video_{schema_name}_{instance.pk}",
        "Plio": f"plio_{schema_name}_{instance.pk}",
        "Item": f"item_{schema_name}_{instance.pk}",
        "Question": f"question_{schema_name}_{instance.pk}",
        "Image": f"image_{schema_name}_{instance.pk}",
        "Experiment": f"experiment_{schema_name}_{instance.pk}",
        "Tag": f"tag_{schema_name}_{instance.pk}",
        # instances that are not tenant specific
        "User": f"user_{instance.pk}",
        "UserMeta": f"user_meta_{instance.pk}",
        "Organization": f"organization_{instance.pk}",
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
