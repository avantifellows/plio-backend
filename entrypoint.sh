#!/bin/bash
set -e

# collect static files
python manage.py collectstatic --no-input

# run migrations
python manage.py migrate

# create default tenant
python manage.py pliotenant

# create default superuser
python manage.py pliosuperuser

# start the server
python manage.py runserver 0.0.0.0:${APP_PORT}

exec "$@"
