# plio-backend

## About This Project
Django-based backend for the Plio interactive video platform. Multi-tenant architecture using django-tenants with PostgreSQL schema separation per organization.

## Tech Stack
- **Framework:** Django 3.2.25
- **Language:** Python 3.8 (Docker/CI), Python 3.10.4 (local dev)
- **Database:** PostgreSQL (via django-tenants for multi-tenancy)
- **Cache/Channels:** Redis (django-redis, channels_redis)
- **Auth:** django-rest-framework-social-oauth2 (Google OAuth2), django-oauth-toolkit, OTP
- **API:** djangorestframework 3.12.2, drf-yasg 1.20.0

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
- `django-request-logging==0.7.2` is incompatible with Django 3.2 (uses `response._headers` removed in 3.2). Upgraded to 0.7.5.
- `requirements-dev.txt` includes `-r requirements.txt` — do not re-pin packages at different versions in dev.
- `entrypoint.sh` runs `makemigrations` on startup (not `--check`), so unexpected migrations are a deployment risk.

## Key Directories
- `plio/` — Core app (models, views, signals for Plio/Video/Item/Question/Image)
- `organizations/` — Multi-tenant organization management
- `users/` — User management, OTP auth
- `entries/` — Session tracking (Session, SessionAnswer, Event)
- `experiments/` — A/B experiment management
- `tags/` — Tagging system
- `etl/` — BigQuery job tracking
