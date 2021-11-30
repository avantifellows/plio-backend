#!/bin/bash
set -e

# collect static files
python manage.py collectstatic --no-input

# create migrations
python manage.py makemigrations

# run migrations
python manage.py migrate

# create default tenant
python manage.py createtenant

# create default superuser
python manage.py createsuperuser

# create default OAuth2 API client credentials
python manage.py createoauth2application

# start the server
python manage.py runserver 0.0.0.0:${APP_PORT}

exec "$@"
