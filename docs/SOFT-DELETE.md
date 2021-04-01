## Soft Deletion
When models are soft deleted, they are not actually removed from your database. Instead, a deleted attribute is set on the model indicating the date and time at which the model was "deleted".

Plio uses the [Django Safedelete](https://pypi.org/project/django-safedelete/) package to implement soft deletion on the models.

### Adding soft delete to a model
1. Create a new model class. Instead of extending `Models.model`, use `SafeDeleteModel` as the base class for your model. This extends the original `Models.model` class and adds methods for soft deletion functionality. Also make sure to define the deletion policy for your model.
    ```py
    from safedelete.models import SafeDeleteModel, SOFT_DELETE

    class MyModel(SafeDeleteModel):
        _safedelete_policy = SOFT_DELETE
        ...
    ```
2. Create migration for your model/app. You will notice a new migration created to add `deleted` column.
    ```sh
    python manage.py makemigrations myapp
    ```
3. Run the migrations. This will create a new DATETIME column `deleted` in the corresponding table.
    ```sh
    python manage.py migrate.
    ```
4. When deleting a row using Django's ORM, the row will not be deleted from the database. Instead the deleted column will not be nullable anymore and store the time of deletion of the row. The row will be filtered out from every operation of that model (LCRUD).
