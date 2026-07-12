---
name: tenancy-and-caching
description: Working safely with tenant schemas and the tenant-scoped Redis cache — the two cross-cutting systems everything else sits on.
triggers:
  - "tenant"
  - "workspace"
  - "organization header"
  - "cache"
  - "redis"
  - "schema"
edges:
  - target: "context/architecture.md"
    condition: "for the request flow through middleware before changing tenancy behaviour"
last_updated: 2026-07-11
---

# Tenancy & Caching

## Context
The `Organization` header picks the Postgres schema per request (middleware in
`organizations/middleware.py`); no header means the default tenant. The Redis cache embeds the
schema in keys for tenant entities (`plio_<schema>_<id>`) and not for global ones (`user_<id>`)
— all key building and invalidation lives in `plio/cache.py`.

## Steps
1. Read `docs/MULTITENANCY.md` and `docs/CACHING.md` for the canonical shell recipes before touching either system.
2. For any query, know which schema you're on — inside a request it's set by the header; in shell/scripts you must set it explicitly before querying tenant models.
3. To operate on another workspace mid-request (cross-tenant features), follow `PlioViewSet.copy`: switch the connection schema deliberately, do the work, and invalidate the destination's cache keys.
4. When adding cached reads: add the key builder to `plio/cache.py`, and hook invalidation into every mutation path (including bulk operations and cross-tenant copies).
5. Raw SQL (in `plio/queries.py`) executes against the current connection schema — verify the schema before running, and filter soft-deleted rows explicitly.

## Gotchas
- The header value is an org shortcode, not an id or schema name — an unknown shortcode silently falls back to the default tenant instead of erroring
- Users/organizations are shared (public schema); sessions/plios/items are tenant data — a join across that boundary needs care
- Cache keys built anywhere except `plio/cache.py` will eventually diverge from the invalidation logic — that's the whole reason the helpers exist
- After a cross-tenant write, invalidating the *source* tenant's keys does nothing — invalidate in the *destination* schema context

## Verify
- [ ] Behaviour correct for: valid header, missing header (default tenant), unknown shortcode
- [ ] Tenant isolation: data written in workspace A is not readable from workspace B
- [ ] Every mutation of a cached entity invalidates through `plio/cache.py`
- [ ] Any manual schema switch restores the original schema afterwards

## Debug
- "Missing" data → print `connection.schema_name` at the failure point; 9 times out of 10 you're on the wrong schema
- Stale entity after update → grep the mutation path for a missing invalidate call
- Works in tests, breaks live → tests may run on the default tenant only; add an org-tenant test case

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" if what's working/not built has changed
- [ ] Update any `.mex/context/` files that are now out of date
- [ ] If this is a new task type without a pattern, create one in `.mex/patterns/` and add to `INDEX.md`
