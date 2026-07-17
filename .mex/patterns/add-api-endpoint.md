---
name: add-api-endpoint
description: Adding a new DRF resource (model + serializer + viewset + route) or a custom action on an existing viewset.
triggers:
  - "new endpoint"
  - "new model"
  - "new viewset"
  - "add action"
edges:
  - target: "context/conventions.md"
    condition: "for structure and naming rules before writing code"
last_updated: 2026-07-11
---

# Add an API Endpoint / Resource

## Context
Every resource is a DRF ViewSet registered on the router in `plio/urls.py` under `/api/v1/`.
Models are soft-deleted (django-safedelete) and may be tenant-scoped (live in a TENANT_APPS app)
or shared (SHARED_APPS). Default permission is IsAuthenticated with OAuth2.

## Steps
1. Decide tenancy first: does this data belong to a workspace (tenant schema) or to everyone (public schema)? That decides which app it lives in and how it migrates.
2. Add the model with the appropriate safedelete policy; generate the migration and inspect it before applying.
3. Add a serializer; keep expansion of related objects deliberate — expensive expansions (like UserSerializer) need filtered list endpoints, not full lists.
4. Add the ViewSet; custom behaviours go in actions (like PlioViewSet's play/duplicate/copy/metrics) rather than new ad-hoc views.
5. Register on the router in `plio/urls.py`.
6. If reads are hot, wire caching through `plio/cache.py` — add the key builder there and invalidate on mutation.
7. Add `APITestCase` tests in the owning app hitting the real endpoint, including one request with an `Organization` header and one without.

## Gotchas
- A model in the wrong SHARED_APPS/TENANT_APPS bucket migrates into every schema (or none) — this is the most expensive mistake in this codebase
- Soft delete + unique constraints interact: a "deleted" row still occupies unique values unless the constraint accounts for it
- Custom permissions: resource-level rules follow the PlioPermission example, driven by org membership (OrganizationUser) and the header workspace

## Verify
- [ ] Migration reviewed: right app bucket, no surprise changes to other apps
- [ ] Endpoint behaves correctly with and without an `Organization` header
- [ ] Cache invalidation covered if the entity is cached
- [ ] Tests added and `docker-compose exec web python manage.py test` passes
- [ ] `pre-commit run --all-files` clean

## Debug
- 404 on a route you just added → router registration in `plio/urls.py` (check the basename)
- Data appearing in the wrong workspace → the model's app is in the wrong tenancy bucket
- Stale reads after writes → missing invalidation call in the mutation path

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" if what's working/not built has changed
- [ ] Update any `.mex/context/` files that are now out of date
- [ ] If this is a new task type without a pattern, create one in `.mex/patterns/` and add to `INDEX.md`
