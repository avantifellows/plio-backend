## Multitenancy
Plio uses the [django-tenants-schemas](https://django-tenant-schemas.readthedocs.io/en/latest/install.html) package to implement multitenancy.

This guide aims to provide details on how Plio is using multi-tenancy and pre-requisites for someone contributing to the code.

### Creating an organization
Run the following commands to create an organization from programmatically:

1. Get into python shell.
    ```sh
    python3 manage.py shell
    ```

2. Create a public tenant that will be the default one.
    ```py
    # create your public tenant
    from organizations.models import Organization, Domain

    tenant = Organization(schema_name='public', name='Plio', shortcode='plio')
    tenant.save()

    domain = Domain()
    domain.domain = 'plio.in'
    domain.tenant = tenant
    domain.is_primary = True
    domain.save()
    ```

3. Create a tenant organization that will have it's own schema.
    ```py
    # create your first real tenant
    tenant = Organization(schema_name='avantifellows', name='Avanti Fellows', shortcode='af')
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
    SELECT tablename FROM pg_catalog.pg_tables where schemaname='avantifellows';
    ```
