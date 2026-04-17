# plio-backend

## About This Project
Django-based backend for the Plio interactive video platform. Multi-tenant architecture using django-tenants with PostgreSQL schema separation per organization.

## Tech Stack
- **Framework:** Django 4.2.30
- **Language:** Python 3.8 (Docker/CI), Python 3.10.4 (local dev)
- **Database:** PostgreSQL 12+ (via django-tenants 3.5.0 for multi-tenancy; docker-compose uses 14-alpine)
- **Cache/Channels:** Redis (django-redis, channels 4.1.0, channels_redis 4.0.0)
- **ASGI Server:** daphne 4.0.0
- **Auth:** django-rest-framework-social-oauth2 1.2.0 (Google OAuth2), django-oauth-toolkit, OTP
- **API:** djangorestframework 3.14.0, drf-yasg 1.21.8

## Commands
```bash
# Testing (requires DB + Redis running, plus env vars)
SECRET_KEY="testsecretkey123" DB_HOST="127.0.0.1" DB_PORT="5432" DB_NAME="plio" DB_USER="postgres" DB_PASSWORD="" REDIS_HOSTNAME="127.0.0.1" REDIS_PORT="6379" python manage.py test

# System check
python manage.py check

# Migration check (no unexpected migrations)
python manage.py makemigrations --check --dry-run
```

## Quality Checks
Before each commit, run:
1. `python manage.py test` — all non-S3 tests must pass (9 S3 image tests require real AWS credentials)
2. `python manage.py check` — no errors
3. `python manage.py makemigrations --check --dry-run` — no unexpected migrations

## Known Gotchas
- 9 tests (ImageTestCase, PlioTestCase copying/duplicate, QuestionTestCase delete-linked-image) require real AWS S3 credentials and will fail locally without them. CI provides these via GitHub secrets.
- `django-request-logging==0.7.5` handles Django 3.2+ `response.headers` (vs deprecated `response._headers`).
- `requirements-dev.txt` includes `-r requirements.txt` — do not re-pin packages at different versions in dev.
- `entrypoint.sh` runs `makemigrations --check --dry-run` scoped to project apps on startup — this catches model drift but does not auto-create migrations.
- `social_django 5.1.0` has an internal migration inconsistency (AppConfig says AutoField, migration 0011 says BigAutoField). Run `makemigrations --check --dry-run plio organizations users entries experiments tags etl` to check only our apps.
- Django 4.0 `MiddlewareMixin.__init__()` requires a `get_response` argument — instantiating middleware outside the request cycle (e.g., in views) needs `get_response=lambda r: None`.
- `drf-social-oauth2==3.2.0` sets `app_name='drf'` in its URLs. `DRFSO2_URL_NAMESPACE = 'drf'` must be set in settings.py.
- `drf-yasg==1.21.15` no longer requires pytz.
- Django 4.2 `STORAGES` dict replaces `DEFAULT_FILE_STORAGE` and `STATICFILES_STORAGE`. Both `"default"` and `"staticfiles"` keys must be present in settings.
- `django-tenants==3.6.1` supports Django 5.0.
- `channels==4.2.0` supports Django 5.0.
- `django-safedelete==1.4.0` adds `deleted_by_cascade` field — migrations generated for all apps.
- Runtime Application lookup uses `client_id=DEFAULT_OAUTH2_CLIENT_ID` (env var), not `name=API_APPLICATION_NAME`.
- `boto3==1.35.99` required for Python 3.12 (old 1.17.90 had broken vendored six).
- `Markdown==3.7` required for Python 3.12 (old 3.3.4 used removed importlib API).
- `six==1.17.0` required for Python 3.12 (old 1.15.0 had broken six.moves).
- `drf-social-oauth2==3.2.0` RevokeTokenView passes hashed `client_secret` from DB into OAuthLib, causing `invalid_client`. Token revocation returns 401; token and convert-token endpoints work fine.
- `requirements-dev.txt` uses `setoptconf-tmp` (not `setoptconf`) — prospector 1.7.7 renamed this dependency.

## Key Directories
- `plio/` — Core app (models, views, signals for Plio/Video/Item/Question/Image)
- `organizations/` — Multi-tenant organization management
- `users/` — User management, OTP auth
- `entries/` — Session tracking (Session, SessionAnswer, Event)
- `experiments/` — A/B experiment management
- `tags/` — Tagging system
- `etl/` — BigQuery job tracking
