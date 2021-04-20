#!/bin/bash
set -e

# run migrations
python manage.py migrate

# create default tenant
python manage.py loaddata organizations/fixtures/default_tenant.yaml

# start the server
python manage.py runserver 0.0.0.0:${APP_PORT}

exec "$@"
