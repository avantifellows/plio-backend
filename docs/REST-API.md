## REST API
Plio uses the [Django REST framework](https://www.django-rest-framework.org/) package to provide the REST API to it's consumers.

This guide aims to provide details on how Plio is using the REST framework and pre-requisites for someone contributing to the code.

### Running API locally
1. Clone the project and start the Django server as mentioned in our [installation guide](INSTALLATION.md).
2. Navigate to `0.0.0.0:8001/api/v1/docs` in your browser and you should see the Plio's detailed API documentation.

### Pre-requisites for contributors
The codebase uses various Django's concepts to provide a rich and meaningful REST API. Please make sure you have a basic understanding of the following concepts:
1. [ViewSets](https://www.django-rest-framework.org/api-guide/viewsets/)
2. [Serializers](https://www.django-rest-framework.org/api-guide/serializers/)
3. [Routers](https://www.django-rest-framework.org/api-guide/routers/)
4. [OpenAPI specifications](https://swagger.io/docs/specification/about/)
5. [Soft deletion](https://en.wiktionary.org/wiki/soft_deletion)

### API Design
Plio considers every entity in the models (or in database) as a resource. A resource can have the following five operations (LCRUD) and the router format.
| Action         | Route format       | METHOD |
|----------------|--------------------|--------|
| List           | `/{resource}/`     | GET    |
| Create         | `/{resource}/`     | POST   |
| Retrieve       | `/{resource}/{id}` | GET    |
| Update         | `/{resource}/{id}` | PUT    |
| Partial update | `/{resource}/{id}` | PATCH  |
| Delete         | `/{resource}/{id}` | DELETE |

In this codebase, resources are users, organizations, plio, items, events, tags, experiments etc. So for user, replace `{resource}` with `user` and `{id}` by the user id.

For more details on routing, visit Django REST Framework's [official documentation](https://www.django-rest-framework.org/api-guide/routers/).
