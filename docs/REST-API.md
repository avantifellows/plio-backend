## REST API
Plio uses the [Django REST framework](https://www.django-rest-framework.org/) package to provide the REST API to it's consumers.

This guide aims to provide details on how Plio is using the REST framework and pre-requisites for someone contributing to the code.

  - [Running API locally](#running-api-locally)
  - [Creating API credentials](#creating-api-credentials)
  - [API Design](#api-design)
  - [Additional help](#additional-help)

### Running API locally
1. Clone the project and start the Django server as mentioned in our [installation guide](INSTALLATION.md).
2. Navigate to `0.0.0.0:8001/api/v1/docs` in your browser and you should see the Plio's detailed API documentation.

### Creating API credentials
1. Create a super user for your backend application. It will ask to set the super user credentials.
    ```sh
    python manage.py createsuperuser
    ```
2. Login to Django admin dashboard from `http://0.0.0.0:8001/admin` and enter your credentials.
3. Add a new Application with the following configuration:
   - `client_id` and `client_secret` should be left unchanged
   - user should be your superuser
   - `redirect_uris` should be left blank
   - `client_type` should be set to confidential
   - `authorization_grant_type` should be set to 'Resource owner password-based'
   - name should be "plio" (all lowercase)
4. Use the client id and client secret in your frontend application or Postman app to make API calls.

### API Design
Plio considers every entity in the models (or in database) as a resource. A resource can have the following operations (LCRUD) that can be run at corresponding route format & request method.

| Action         | Route format       | Method |
|----------------|--------------------|--------|
| List           | `/{resource}/`     | GET    |
| Create         | `/{resource}/`     | POST   |
| Retrieve       | `/{resource}/{id}` | GET    |
| Update         | `/{resource}/{id}` | PUT    |
| Partial update | `/{resource}/{id}` | PATCH  |
| Delete         | `/{resource}/{id}` | DELETE |

In this codebase, resources are users, organizations, plio, items, events, tags, experiments etc. So for user, replace `{resource}` with `user` and `{id}` by the user id.

For more details on routing, visit Django REST Framework's [official documentation](https://www.django-rest-framework.org/api-guide/routers/).

### Additional help
The codebase uses various Django's concepts to provide a rich and meaningful REST API:
1. [ViewSets](https://www.django-rest-framework.org/api-guide/viewsets/)
2. [Serializers](https://www.django-rest-framework.org/api-guide/serializers/)
3. [Routers](https://www.django-rest-framework.org/api-guide/routers/)
4. [OpenAPI specifications](https://swagger.io/docs/specification/about/)
