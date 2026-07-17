---
name: agents
description: Always-loaded project anchor. Read this first. Contains project identity, non-negotiables, commands, and pointer to ROUTER.md for full context.
last_updated: 2026-07-11
---

# Plio Backend

## What This Is
Multi-tenant Django REST API powering Plio — interactive video lessons: creators build plios (video + timed questions), learners watch and answer; every workspace is an isolated Postgres schema.

## Non-Negotiables
- Respect tenancy on every data access — the `Organization` request header selects the Postgres schema (django-tenants); never query across schemas without an explicit schema switch
- Deletes are soft deletes (django-safedelete) everywhere — never hard-delete rows or write raw SQL deletes
- Invalidate the Redis cache through the helpers in `plio/cache.py` whenever a cached entity mutates — keys are tenant-scoped
- Never commit secrets — `.env` is gitignored; document new vars in `.env.example` and `docs/ENV.md`
- Never edit an applied migration; new models must be placed correctly in SHARED_APPS vs TENANT_APPS in `plio/settings.py`

## Commands
- Run (docker): `docker-compose up -d --build` — API at http://0.0.0.0:8001/api/v1, admin at /admin
- Test: `docker-compose exec web python manage.py test` (CI runs `coverage run manage.py test`)
- Lint: `pre-commit run --all-files` (black + flake8)
- Migrations: `docker-compose exec web python manage.py makemigrations` / `migrate`

## Scaffold Growth
After meaningful work, run GROW:
- Ground: what changed in reality?
- Record: update `ROUTER.md` and relevant `context/` files
- Orient: create or update a `patterns/` runbook if this can recur
- Write: bump `last_updated` on changed scaffold files and run `mex log` when rationale matters

## Navigation
At the start of every session, read `ROUTER.md` before doing anything else.
For full project context, patterns, and task guidance — everything is there.
