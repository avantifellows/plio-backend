---
name: agents
description: Always-loaded project anchor. Read this first. Contains project identity, non-negotiables, commands, and pointer to ROUTER.md for full context.
last_updated: 2026-07-14
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
- Test (pytest, one runner, two lanes): unit `docker-compose exec web pytest --ignore=tests/integration`; integration `docker-compose exec web pytest -m integration` (CI runs each lane under `coverage run -m pytest ...`)
- Lint: `pre-commit run --all-files` (black + flake8)
- Migrations: `docker-compose exec web python manage.py makemigrations` / `migrate`

## Testing (backend test wall, #374)
- One pytest runner, two lanes: the unit lane is everything outside `tests/integration/`; the integration lane is `pytest -m integration` (API journeys through the real app, tenant Postgres, and Redis). Legacy `APITestCase` tests run unchanged.
- Integration specs never call `connection.set_schema()` — select the tenant via the `Organization` header (actor fixtures) and switch schemas only through the `in_workspace(...)` builder. Reuse `tests/factories.py`, `tests/builders.py`, and the `creator`/`learner` actor fixtures; keep slice-local helpers in the spec module, shared ones in the harness.
- Redis cleanup is per-worker `flushdb`, never `flushall` (xdist workers each own a logical DB). Commit-requiring specs (the websocket canary) are marked `slow_lane` with truncation cleanup; `pytest -m "integration and not slow_lane"` excludes them.
- Metrics, scorecard, watch-time, and CSV-cell expectations are hand-computed literals from a small constructed timeline — never recomputed by re-running the app's own aggregation.
- Unit-lane DB specs (model/serializer seams — the per-app fills like `tests/test_plio_queries.py`, `tests/test_session_carryover.py`) also build data inside `in_workspace(org_a)` on the shared factories with hand-worked literal oracles, never call `set_schema`, and keep one edge per named spec. To exercise a DRF serializer's create/update path in the unit lane, drive it directly with a slice-local fake view context (`SimpleNamespace(action="create")`) and an explicitly passed `user` — no HTTP client. Soft-delete edges use the model's own `delete()` (never `all_objects` or raw SQL); observed product quirks are pinned as-is in a spec docstring, not fixed.
- SHARED_APPS unit fills are the deliberate exception to `in_workspace(...)`: apps whose tables live in the public schema (the users app — `User`, `Role`, `OrganizationUser`) build rows directly with the shared factories, no `in_workspace(...)` and no `set_schema` anywhere (e.g. `tests/test_users_filters.py`). Org context is then selected only via the `Organization` request header on the actor call — `caller.get(url, organization=org_a)` sets the header from the workspace shortcode, while a raw `HTTP_ORGANIZATION=` sends an unknown shortcode that the tenant middleware falls back to the public schema, keeping header-dependent view branches (e.g. `RoleViewSet`'s visibility matrix) reachable at the HTTP list seam. Flag the shared-schema deviation in the module docstring.
- Coverage: `.coveragerc` (branch-on, app-scoped); committed floors in `coverage_floors/<lane>` enforced by `scripts/check_coverage_floor.py` in CI. Floors only ratchet up — bump the floor in the same PR when the job summary nudges (measured >~2% above floor). Never lower a floor to make a build pass.

## After Every Task
After meaningful work, run GROW:
- Ground: what changed in reality?
- Record: update `.mex/ROUTER.md` and relevant `.mex/context/` files
- Orient: create or update a `.mex/patterns/` runbook if this can recur
- Write: bump `last_updated` on changed scaffold files and run `mex log` when rationale matters

## Navigation
At the start of every session, read `.mex/ROUTER.md` before doing anything else.
For full project context, patterns, and task guidance — everything is there.
