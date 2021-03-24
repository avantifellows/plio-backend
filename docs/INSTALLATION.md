## Installation


### Pre-requisites
#### Python
Required version `3.8.2`

#### Database setup
Plio backend uses Postgres SQL database. Use the instructions below to set up the database server on your operating system.

1. macOS

    Use brew to install Postgres
    ```sh
    brew install postgresql
    ```

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
4. Create a new database in your Postgres
5. Set up your .env file by copying .env.example
    ```sh
    cp .env.example .env
    ```
6. Update variables in your `.env` file based on your settings.
7. Database setup: Plio is a multi-tenant app that uses semi-isolated database structure: shared database, separate schemas. One database for all tenants, but one schema per tenant using the [django-tenants](https://django-tenants.readthedocs.io/en/latest/) package.

    - Run migrations to create the shared (public) schema
        ```sh
        python manage.py migrate_schemas --shared
        ```
    - You can also create tenants by using the commands [here](https://django-tenants.readthedocs.io/en/latest/use.html)

8. For **development purpose** only, run the following command to install pre-commit
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
