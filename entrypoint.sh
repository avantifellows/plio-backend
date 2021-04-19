#!/bin/bash
set -e

# start server
python manage.py migrate && python manage.py runserver 0.0.0.0:${APP_PORT}

# create default tenant
python manage.py loaddata organizations/fixtures/default_tenant.yaml


exec "$@"
