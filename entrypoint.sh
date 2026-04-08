#!/bin/bash
set -e

# collect static files
python manage.py collectstatic --no-input

# check for unexpected migrations in our apps (fail fast on model drift)
python manage.py makemigrations --check --dry-run plio organizations users entries experiments tags etl

# run migrations
python manage.py migrate

# create default tenant
python manage.py createtenant

# create default superuser
python manage.py createdefaultsuperuser

# create default OAuth2 API client credentials
python manage.py createoauth2application

# start the ASGI server via daphne
daphne -b 0.0.0.0 -p ${APP_PORT} plio.asgi:application

exec "$@"
