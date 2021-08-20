#!/bin/bash
set -e

# collect static files
python manage.py collectstatic --no-input

# create migrations
python manage.py makemigrations

# run migrations
python manage.py migrate

# create default tenant
python manage.py pliotenant

# create default superuser
python manage.py pliosuperuser

# start the server
gunicorn plio.wsgi:application --bind 0.0.0.0:8001 --workers 4 --timeout 600 --reload

exec "$@"
