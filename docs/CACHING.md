## Caching
Plio uses the Redis cache backend powered by the [Django Redis](https://github.com/jazzband/django-redis) package.

This guide aims to provide details on how Plio is using caching and pre-requisites for someone contributing to the code.

### Caching workflow
Plio's caching mechanism can be explained in three simple steps:
1. Receives an API request
2. Searches for the requested data in the cache
3. If not present, query the database and save the response in cache for future requests

![Overview of caching](images/caching-workflow.png)


### Cache keys
The calculation of the cache keys are based on the model instances. For example, an instance for plio ID: 1 will have `plio_1` as the cache key.
For more details, check out the `get_cache_key` function in `plio/cache.py`.


### Cache refresh or invalidation
When a particular instance is updated, it's cached value gets deleted along with any other related instances cache that depends on this cache. For example, if a session instance cache uses plio instance cache in it's response, if the plio is modified, both plio instance and session instance cache will be deleted.

The new cache will be set during the first fresh response calculated from the database and will be used for subsequent requests.
