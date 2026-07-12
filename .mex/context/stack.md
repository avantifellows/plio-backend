---
name: stack
description: Technology stack, library choices, and the reasoning behind them. Load when working with specific technologies or making decisions about libraries and tools.
triggers:
  - "library"
  - "package"
  - "dependency"
  - "which tool"
  - "technology"
edges:
  - target: context/decisions.md
    condition: when the reasoning behind a tech choice is needed
  - target: context/conventions.md
    condition: when understanding how to use a technology in this codebase
last_updated: 2026-07-11
---

# Stack

## Core Technologies

- **Python 3.8** (CI target) with **Django 3.1.1** on main — a migration chain to Django 5.2.14 LTS exists as unmerged PRs #354–#360; don't use newer Django APIs on main
- **Django REST Framework 3.12.2** — every endpoint is a DRF ViewSet routed under `/api/v1/`
- **PostgreSQL 11** — schema-per-tenant via django-tenants
- **Redis 5** — cache backend and channels layer
- **Docker Compose** — the supported dev environment (services: db, web, redis)

## Key Libraries

- **django-tenants 3.2.1** — multi-tenancy backbone; SHARED_APPS vs TENANT_APPS split in `plio/settings.py`
- **django-safedelete 1.0.0** — soft delete on models; deleted rows stay in the table
- **django-rest-framework-social-oauth2 1.1.0** — Google login token conversion; internal OAuth2 provider issues access/refresh tokens
- **channels 3.0.3** + **channels_redis** — WebSocket support (ASGI)
- **django-redis 5.0.0** — cache; always use the helpers in `plio/cache.py`, not raw cache calls, so keys stay tenant-scoped
- **pandas** + **pyarrow** — metrics/report post-processing over raw SQL from `plio/queries.py`
- **boto3 / django-storages** — S3 image storage and SNS SMS
- **drf-yasg 1.20.0** — API docs at `/api/v1/docs/`
- **django-silk** — profiling in local/staging; **sentry-sdk** — error monitoring
- **coverage 5.5** — test coverage (CI uploads to Codecov)

## What We Deliberately Do NOT Use

- No celery/task queue — nothing here should assume async background workers exist
- No pytest — tests are Django `TestCase`/DRF `APITestCase` style, run with `manage.py test`
- No raw `cache.set/get` with hand-built keys — tenant-scoped key builders in `plio/cache.py` only
- No ORM `.delete()` semantics assumptions — safedelete changes behaviour; see the soft-delete pattern

## Version Constraints

- Main is intentionally frozen on old pins (Django 3.1.1, DRF 3.12.2) until the migration PR chain (#354–#360) merges — the chain must merge in order, oldest first
- django-request-logging 0.7.2 is abandoned upstream; keep it until its replacement PR (deferred, post-migration)
