## Caching
Plio uses the Redis cache backend powered by the [Django Redis](https://github.com/jazzband/django-redis) package.

This guide aims to provide details on how Plio is using caches and serves as a pre-requisite for someone contributing to the code.

### Caching workflow
Plio's caching mechanism can be explained in three simple steps:
1. Receives an API request
2. Searches for the requested data in the cache
3. If not present, query the database and save the response in cache for future requests

##### Caching workflow explained via flow diagram
![Overview of caching](images/caching-workflow.png)


### Cache keys
The calculation of the cache keys are based on the model instances. For example, an instance for plio ID: 1 will have `plio_1` as the cache key.
For more details, check out the `get_cache_key` function in `plio/cache.py`.


### Cache invalidation
When a particular instance is updated, its cached value gets deleted along with the cache of any other related instances that depends on this cache. For example, consider a session instance cache that uses a plio instance cache. Now, if the plio is modified, the caches for both the plio instance and the session instance will be deleted.

The new cache will be set when the first fresh response is calculated from the database and will be used for subsequent requests.

##### Cache invalidation explained via flow diagram
![Overview of caching](images/cache-invalidation-workflow.png)


### Current cached data
We have only implemented caching for models with a high number of GET requests. The following resources have been cached:
1. #### Plio
    - Plio cache is created when there is a retrieve request for a plio instance.
    - Plio cache is re-created when there is a create, update or delete request for a plio instance.
    - Plio cache is deleted when there is a create, update or delete request for any of the following related instances for a plio instance:
        - Video
        - Item
        - Question
        - User


2. #### User
    - User cache is created when there is a retrieve request for a user instance.
    - User cache is re-created when there is a create, update or delete request for any of the following related instances:
      - User
      - OrganizationUser (as the `UserSerializer` is called when `OrganizationUser` is modified)
    - User cache is deleted when there is a create, update or delete request for any of the following related instances for a user instance:
        - Organization

For more details on the caching implementation for above, refer to the corresponding `serializers.py` files.
