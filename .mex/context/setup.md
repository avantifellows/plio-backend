---
name: setup
description: Dev environment setup and commands. Load when setting up the project for the first time or when environment issues arise.
triggers:
  - "setup"
  - "install"
  - "environment"
  - "getting started"
  - "how do I run"
  - "local development"
edges:
  - target: context/stack.md
    condition: when specific technology versions or library details are needed
  - target: context/architecture.md
    condition: when understanding how components connect during setup
last_updated: 2026-07-11
---

# Setup

## Prerequisites

- Docker Desktop (the supported dev flow — Postgres, Redis, and the app all run in compose)
- pre-commit (`pip install pre-commit` or `brew install pre-commit`) for the git hooks
- Python 3.8 if running outside docker (CI uses 3.8)

## First-time Setup

1. `cp .env.example .env` and fill values (full reference: `docs/ENV.md`)
2. `docker-compose up -d --build` — brings up db (postgres:11), redis (redis:5), and web
3. `pre-commit install` (dev only)
4. Configure a login method: OTP (`docs/ONE-TIME-PIN.md`) or Google sign-in (docs/oauth/ guide)
5. API at http://0.0.0.0:8001/api/v1 — docs at /api/v1/docs/ — Django admin at http://0.0.0.0:8001/admin
6. Full walkthrough: `docs/INSTALLATION.md`

## Environment Variables

- `SECRET_KEY`, `DEBUG`, `APP_ENV`, `ALLOWED_HOSTS`, `APP_PORT` (required) — core Django/runtime
- `DB_ENGINE`, `DB_HOST`, `DB_NAME`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` (required) — Postgres; in docker, `DB_HOST=db`
- `REDIS_HOSTNAME`, `REDIS_PORT` (required) — cache + channels
- `DEFAULT_TENANT_NAME`, `DEFAULT_TENANT_SHORTCODE`, `DEFAULT_TENANT_DOMAIN` (required) — the fallback public tenant
- `SUPERUSER_EMAIL`, `SUPERUSER_PASSWORD` (required) — bootstrap admin
- `DEFAULT_OAUTH2_CLIENT_SETUP`, `DEFAULT_OAUTH2_CLIENT_ID`, `DEFAULT_OAUTH2_CLIENT_SECRET` (required) — internal OAuth app (also via `python manage.py createoauth2application`)
- `GOOGLE_OAUTH2_CLIENT_ID`, `GOOGLE_OAUTH2_CLIENT_SECRET` (required for Google login)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (required for S3 images / SNS OTP), `AWS_STORAGE_BUCKET_NAME` (S3), `SMS_DRIVER` (`sns` to send real SMS)
- `SENTRY_DSN` (optional) — error monitoring

## Common Commands

- `docker-compose up -d --build` — build and start the full stack
- `docker-compose exec web python manage.py test` — run the test suite in the container
- `coverage run manage.py test` — how CI runs tests (then uploads to Codecov)
- `docker-compose exec web python manage.py makemigrations` / `migrate` — schema changes
- `docker-compose exec web python manage.py shell` — Django shell (tenant-aware helpers in `docs/MULTITENANCY.md`)
- `pre-commit run --all-files` — black + flake8 + hygiene hooks
- `docker-compose logs -f web` — tail app logs

## Common Issues

**DB connection refused from the app:** `DB_HOST` must be `db` (the compose service name) inside docker — `localhost` only works from the host machine.
**401s on every endpoint after fresh setup:** no OAuth2 application exists yet — set the `DEFAULT_OAUTH2_CLIENT_*` vars or run `python manage.py createoauth2application`, and make sure the frontend uses the same client id/secret.
**Wrong or empty data for a workspace:** the request's `Organization` header doesn't match an existing tenant shortcode, so it fell back to the default tenant.
**Migrations touching apps you didn't change:** check the SHARED_APPS/TENANT_APPS split in `plio/settings.py` before applying — a model in the wrong bucket migrates into every schema.
