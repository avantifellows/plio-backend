#!/bin/bash
set -e

python manage.py loaddata organizations/fixtures/default_tenant.yaml

exec "$@"
