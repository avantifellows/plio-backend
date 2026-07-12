---
name: decisions
description: Key architectural and technical decisions with reasoning. Load when making design choices or understanding why something is built a certain way.
triggers:
  - "why do we"
  - "why is it"
  - "decision"
  - "alternative"
  - "we chose"
last_updated: 2026-07-11
---

# Decisions

## Decision Log

### Schema-per-workspace multi-tenancy with django-tenants
**Date:** 2021 (original architecture, verified 2026-07-11)
**Status:** Active
**Decision:** Each organization/workspace gets its own Postgres schema; the `Organization` request header (org shortcode) selects the schema via middleware; shared models (users, organizations) live in the public schema.
**Reasoning:** Hard isolation of workspace data (learner sessions, plios) with one database to operate; a header-based switch keeps the API surface identical for all tenants.
**Alternatives considered:** Row-level tenancy with a foreign key (rejected — weaker isolation, every query must remember the filter).
**Consequences:** Every request without the header lands on the default tenant; cross-workspace features (plio copy) must switch schemas explicitly; cache keys must embed the schema name.

### Soft delete everywhere via django-safedelete
**Date:** 2021 (original architecture, verified 2026-07-11)
**Status:** Active
**Decision:** Models use safedelete policies instead of hard deletion.
**Reasoning:** Learner data and creator content are analytically valuable and deletion is often accidental; recovery beats backups.
**Consequences:** Unique constraints and counts must account for soft-deleted rows; default managers exclude them, which surprises raw SQL (queries in `plio/queries.py` must filter deleted rows themselves).

### Issue internal OAuth2 tokens for every auth flow
**Date:** 2021 (original architecture, verified 2026-07-11)
**Status:** Active
**Decision:** Google login, OTP, and third-party SSO all converge on the same internal OAuth2 provider — external identity is exchanged for a Plio access/refresh token pair.
**Reasoning:** One authorization model downstream: DRF permissions only ever see internal Bearer tokens regardless of how the user logged in.
**Consequences:** Third parties integrate by exchanging their org `api_key` + user `unique_id` at `/auth/generate-external-auth-access-token/`; token lifetime/refresh policy is controlled centrally.

### Upgrade Django via a chained, reviewable PR sequence
**Date:** 2026-05-06
**Status:** Active (chain unmerged as of 2026-07-11)
**Decision:** Move master from Django 3.1.1 to 5.2.14 LTS through stepwise PRs (#354–#360), one Django version hop each (3.2 → 4.0 → 4.1 → 4.2 → 5.0 → 5.1 → 5.2), each validated by the full test suite plus added smoke tests.
**Reasoning:** A single mega-upgrade of a 4-major-version gap across tenants, soft delete, channels, and OAuth is unreviewable and undebuggable; per-version PRs isolate breakage.
**Alternatives considered:** Direct 3.1 → 5.2 jump (rejected — too many interacting breaking changes).
**Consequences:** PRs must merge in order, oldest first; master stays on old pins until then; sentry-sdk/daphne upgrades and the django-request-logging replacement are deliberately deferred to separate follow-up PRs.
