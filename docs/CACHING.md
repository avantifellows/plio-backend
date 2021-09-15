## Caching
Plio uses the Redis cache backend powered by the [Django Redis](https://github.com/jazzband/django-redis) package.

This guide aims to provide details on how Plio is using caching and pre-requisites for someone contributing to the code.

### Caching workflow
Plio's caching mechanism can be explained in three simple steps:
1. Receives an API request
2. Searches for the requested data in the cache
3. If not present, query the database and save the response in cache for future requests

![Overview of caching](images/caching-workflow.png)


Run the following commands to create an organization from programmatically:

1. Get into python shell.
    ```sh
    python3 manage.py shell
    ```

2. Create a public tenant that will be the default one.

    **Note:** Public tenant is already created when docker container is initialized through Django fixtures. Please refer `entrypoint.sh` and `organizations/fixtures/default_tenant.yaml` files.

    ```py
    # create your public tenant
    from organizations.models import Organization, Domain

    tenant = Organization(schema_name='public', name='Plio', shortcode='plio')
    tenant.save()

    domain = Domain()
    domain.domain = 'plio.in' # use domain.domain = '0.0.0.0' for development environment
    domain.tenant = tenant
    domain.is_primary = True
    domain.save()
    ```

3. Create a tenant organization that will have it's own schema.
    ```py
    # create your first real tenant
    tenant = Organization(name='Avanti Fellows', shortcode='af')
    tenant.save()

    domain = Domain()
    domain.domain = 'plio.in/avantifellows'
    domain.tenant = tenant
    domain.is_primary = True
    domain.save()
    ```

4. Now log into your PostgreSQL database server. Run the following command to list all the schemas. You will see various schemas along with the two above: `public` and `avantifellows`
    ```sql
    SELECT schema_name FROM information_schema.schemata;
    ```

5. List tables from `public` and `avantifellows` schemas. You will notice that both schemas have basic tables for plio related things but public schema will also have tables for organization and user.
    ```sql
    -- view tables in public schema
    SELECT tablename FROM pg_catalog.pg_tables where schemaname='public';

    -- view tables in tenant organization schema
    SELECT tablename FROM pg_catalog.pg_tables where schemaname='generated_schema_name';
    ```
