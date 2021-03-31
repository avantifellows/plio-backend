## Installation


### Pre-requisites
#### Python
Required version `3.8.2`

#### Database setup
Plio backend uses Postgres SQL database. Use the instructions below to set up the database server on your operating system.

1. macOS
    - Use brew to install Postgres
        ```sh
        brew install postgresql           # install postgresql
        brew services start postgresql    # start postgresql
        ```
     - Check your installation by running
        ```sh
        psql
        ```
        If you get an error saying `error: psql: error: FATAL:  database "{USER_NAME}" does not exist`, run the following command before entering `psql`:
        ```sh
        createdb
        ```
     - If everything works correctly, you should be inside the PostgreSQL shell


2. Windows
    - Download [Postgres server](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
    - Ensure that the installation includes the PostgreSQL Unicode ODBC driver. (Not required if you selected all options while installing)
    - _Note_: Once installed, the PostgreSQL server appears in the `Services` tab in Windows Task Manager.
    - Add the PostgreSQL bin directory path to the `PATH` environmental variable
    - Confirm the installation by typing `psql` in the Command Prompt


### Installation steps
1. Clone the repository and change the working directory
    ```sh
    git clone https://github.com/avantifellows/plio-backend.git
    cd plio-backend
    ```
2. Create a virtual environment and activate it
    ```sh
    python3 -m venv zappa_env
    source zappa_env/bin/activate
    ```
3. Install the dependencies
    #### Development
    ```sh
    pip install -r requirements-dev.txt
    ```

    #### Production
    ```sh
    pip install -r requirements.txt
    ```

    In case of errors in macOS venv, run the following commands to configure OpenSSL properly:
    ```sh
    export LDFLAGS="-L/usr/local/opt/openssl/lib"
    export CPPFLAGS="-I/usr/local/opt/openssl/include"
    ```
4. Create a new database in your Postgres.
    - Open the PostgreSQL command prompt (ensure that you have already started postgres as mentioned above)
        ```sh
        psql
        ```
     - Create a database and user with password
        ```sql
        CREATE DATABASE DATABASE_NAME;
        CREATE USER DATABASE_USER WITH PASSWORD 'DATABASE_PASSWORD';
        ```
        You might see an error saying that an empty password is not allowed if you are using an empty password. The user would be created anyways.
5. Set up your `zappa_settings.json` file by copying `zappa_settings.example.json` file
    ```sh
    cp zappa_settings.example.json zappa_settings.json
    ```
6. Update environment variables in your `zappa_settings.json` file based on your environment. For all available settings, see our [Zappa Settings guide](ZAPPA-SETTINGS.md).
7. Database setup: Plio is a multi-tenant app that uses semi-isolated database structure: shared database, separate schemas. One database for all tenants, but one schema per tenant using the [django-tenants](https://django-tenants.readthedocs.io/en/latest/) package.

    - Run migrations to create the shared (public) schema
        ```sh
        python manage.py migrate_schemas --shared
        ```
    - Create a public tenant in your database
        - Get into python shell.
            ```sh
            python manage.py shell
            ```
        - Run the following commands to a create public tenant. This will be used by the appplication to determine what data to load in the default URL.
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
        - For more details on database seeding and creating tenant organizations, visit our [multitenancy](MULTITENANCY.md) guidelines.

8. For **DEVELOPMENT PURPOSE** only, run the following command to install pre-commit
    ```sh
    pre-commit install
    ```
9. Start the python server
    ```sh
    export DJANGO_ENV=local && python manage.py runserver 0.0.0.0:8001
    ```

    Other possible values for DJANGO_ENV are `staging` and `prod`.

    **Note:** In Windows (even if you're using WSL), if you want to see the static html/css on a browser or hit the API using PostMan, don't use `0.0.0.0:8001`, but use `127.0.0.1:8001` instead.
    > `0.0.0.0` is the invalid, un-routable address. [source](https://news.ycombinator.com/item?id=18978357)
