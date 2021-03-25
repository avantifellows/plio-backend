## Installation


### Pre-requisites
- Python: Required version `3.8.2`


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

4. Set up your zappa_settings.json file by copying zappa_settings.example.json file
    ```sh
    cp zappa_settings.example.json zappa_settings.json
    ```
5. Update environment variables in your `zappa_settings.json` file based on your environment. For all available settings, see our [Zappa Settings guide](ZAPPA-SETTINGS.md).
6. For **development** only, run the following command to install pre-commit
    ```sh
    pre-commit install
    ```
7. Start the python server
    ```
    export DJANGO_ENV=local && python manage.py runserver 0.0.0.0:8001
    ```

    Other possible values for DJANGO_ENV are `staging` and `prod`.

    **Note:** In Windows (even if you're using WSL), if you want to see the static html/css on a browser or hit the API using PostMan, don't use `0.0.0.0:8001`, but use `127.0.0.1:8001` instead.
    > `0.0.0.0` is the invalid, un-routable address. [source](https://news.ycombinator.com/item?id=18978357)

### Database setup
Plio backend uses Postgres SQL database. Use the instructions below to set up the database server on your operating system.

1. macOS

    Use brew to install Postgres
    ```
    brew install postgresql
    ```

2. Windows
    - Download Postgres server from [here](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
    - Ensure that the installation includes the PostgreSQL Unicode ODBC driver. (Not required if you selected all options while installing)
    - _Note_: Once installed, the PostgreSQL server appears in the `Services` tab in Windows Task Manager.
    - Add the PostgreSQL bin directory path to the `PATH` environmental variable
    - Confirm the installation by typing `psql` in the Command Prompt
