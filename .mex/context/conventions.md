---
name: conventions
description: How code is written in this project — naming, structure, patterns, and style. Load when writing new code or reviewing existing code.
triggers:
  - "convention"
  - "pattern"
  - "naming"
  - "style"
  - "how should I"
  - "what's the right way"
edges:
  - target: context/architecture.md
    condition: when a convention depends on understanding the system structure
last_updated: 2026-07-11
---

# Conventions

## Naming

- Django apps are plural lowercase (`users`, `organizations`, `entries`, `experiments`, `tags`) except the core `plio` app; each app follows the standard models/serializers/views/urls layout
- Models: PascalCase singular (Plio, SessionAnswer, OrganizationUser); tables/columns snake_case via Django defaults
- API routes: kebab/plural resource roots under `/api/v1/` (`/plios/`, `/session-answers/`, `/organization-users/`)
- Cache keys: `<entity>_<schema>_<id>` for tenant-scoped entities, `<entity>_<id>` for global ones — built only in `plio/cache.py`
- Code style enforced by black + flake8 through pre-commit (`.pre-commit-config.yaml`)

## Structure

- Every resource is a DRF ViewSet registered on the router in `plio/urls.py` — no function-based API views
- Business logic lives on viewsets/serializers/model methods within the owning app; cross-app imports flow toward `plio` (core), not away from it
- Raw SQL is confined to `plio/queries.py` and always executes against the current tenant schema
- Settings are environment-driven via `.env` (see `docs/ENV.md`); no per-developer settings files
- Tests live in each app (`test_views.py` etc.) and use DRF's `APITestCase` hitting real endpoints

## Patterns

Tenant-aware queries — the schema is set by middleware from the `Organization` header; to touch
another workspace explicitly, switch schema deliberately (as `PlioViewSet.copy` does) and switch
back; never hardcode schema names.

Soft delete — models use django-safedelete, so:

```python
# Correct — respects soft delete
Plio.objects.filter(uuid=uuid).first()  # excludes soft-deleted by default

# Wrong — resurrects or double-counts soft-deleted rows
Plio.objects.all_with_deleted()  # only for explicit undelete/audit flows
```

Cache invalidation — after mutating a cached entity:

```python
from plio.cache import invalidate_cache_for_instance
invalidate_cache_for_instance(instance)  # tenant-scoped key handled for you
```

Serializer expansion cost — UserSerializer expands organizations/roles per user; for lookups use
query params (`/users/?email=<email>` or `?ids=`) instead of listing and filtering in Python.

## Verify Checklist

Before presenting any code:
- [ ] `pre-commit run --all-files` passes (black + flake8)
- [ ] Tests pass: `docker-compose exec web python manage.py test` (or `coverage run manage.py test`)
- [ ] New/changed models: migration generated, placed in the right SHARED_APPS/TENANT_APPS bucket, and no unexpected migrations for other apps
- [ ] Mutations to cached entities invalidate via `plio/cache.py` helpers
- [ ] Endpoint works with an `Organization` header set AND absent (falls back to default tenant)
- [ ] No hard deletes and no raw cache key strings introduced
