---
name: router
description: Session bootstrap and navigation hub. Read at the start of every session before any task. Contains project state, routing table, and behavioural contract.
edges:
  - target: context/architecture.md
    condition: when working on system design, integrations, or understanding how components connect
  - target: context/stack.md
    condition: when working with specific technologies, libraries, or making tech decisions
  - target: context/conventions.md
    condition: when writing new code, reviewing code, or unsure about project patterns
  - target: context/decisions.md
    condition: when making architectural choices or understanding why something is built a certain way
  - target: context/setup.md
    condition: when setting up the dev environment or running the project for the first time
  - target: patterns/INDEX.md
    condition: when starting a task — check the pattern index for a matching pattern file
last_updated: 2026-07-13
---

# Session Bootstrap

If you haven't already read `AGENTS.md`, read it now — it contains the project identity, non-negotiables, and commands.

Then read this file fully before doing anything else in this session.

## Current Project State

**Working:**
- Full REST API (v1): plios, items, questions, videos, images, sessions, session-answers, events, users, organizations, experiments, tags — standard DRF CRUD plus plio actions (play, duplicate, copy, metrics, download_data)
- Three auth flows: Google OAuth (convert-token), OTP over SMS (AWS SNS), and third-party SSO (org api_key + unique_id)
- Schema-per-workspace multi-tenancy, Redis caching with tenant-scoped keys, soft delete everywhere, live user updates over WebSocket (channels)
- ~260 unit tests across users, organizations, entries, and plio apps (CI: coverage + Codecov)

**Not yet built:**
- Django upgrade: main still runs Django 3.1.1 — an unmerged PR chain (#354–#360, branches ralph/django-*-migration) steps 3.1 → 5.2.14 LTS
- API/integration tests that follow real user journeys (creator: create→publish; learner: session→answers) — unit tests cover isolated CRUD only. Planning lives on wayfinder map #362 ("green, comprehensive test wall for the Django upgrade", charted 2026-07-12). Resolved so far: journey inventory (#363 — 9 e2e journeys, integration carries depth), e2e stack survey (#364) and stack decision (#369) — **Playwright**, all 9 journeys sharded per PR, ephemeral in-workflow CI stack, local-first (every layer = one documented local command) as a binding acceptance criterion. Integration harness decided (#367): pytest + pytest-django, session-scoped tenant universe with transaction rollback, real Redis per-xdist-worker DBs, factory_boy + schema-aware builders, a new top-level integration-tests directory organized by journey axis (to be created by the workstream), ≤5-min CI budget. YouTube spike resolved (#371): real playback is hard-blocked on GitHub-hosted runners (datacenter-IP bot wall) — playback-stubbed journeys in CI, real playback in a local `@real-playback` lane. Unit-gap plan decided (#366): surface-based bar (not line-%), experiments + tags consciously skipped (abandoned), four per-app fill issues (plio queries/masking/CSV, entries carryover recursion, users filters/visibility, etl CRUD/perms) in pytest style on the shared factories, gated on the integration harness slice. Coverage & ratchet decided (#368): floors enforced in-repo (committed floor file + CI fail-under), Codecov visibility-only (v5 + token, fail_ci_if_error), scoped .coveragerc + branch coverage with separate unit/integration flags, e2e measured by journey manifest not line-%, one global floor per lane, manual bumps with job-summary nudge. Jest revival decided (#365): pin jest-mock-axios to exact 4.5.0, permanent mixpanel-browser mock, prism-es6 transform exception — 95.6% green verified locally, 17 drifted tests enumerated for test-by-test fixes, no toolchain upgrade (Vue build-tooling ruled out of the map's scope). Frontier: per-PR validation (#370) — last decision ticket; manual tasks: test account (#372), Codecov tokens (#373). No fog remains
- experiments and tags apps have placeholder tests; events, session-answers, images have minimal coverage

**Known issues:**
- Several dependencies are years behind (see requirements.txt pins) until the migration chain merges — don't add code relying on newer Django/DRF APIs on main
- django-request-logging is abandoned upstream; replacement deferred to its own PR (post-migration)

## Routing Table

Load the relevant file based on the current task. Always load `context/architecture.md` first if not already in context this session.

| Task type | Load |
|-----------|------|
| Understanding how the system works | `context/architecture.md` |
| Working with a specific technology | `context/stack.md` |
| Writing or reviewing code | `context/conventions.md` |
| Making a design decision | `context/decisions.md` |
| Setting up or running the project | `context/setup.md` |
| Any specific task | Check `patterns/INDEX.md` for a matching pattern |

## Behavioural Contract

For every task, follow this loop:

1. **CONTEXT** — Load the relevant context file(s) from the routing table above. Check `patterns/INDEX.md` for a matching pattern. If one exists, follow it. Narrate what you load: "Loading architecture context..."
2. **BUILD** — Do the work. If a pattern exists, follow its Steps. If you are about to deviate from an established pattern, say so before writing any code — state the deviation and why.
3. **VERIFY** — Load `context/conventions.md` and run the Verify Checklist item by item. State each item and whether the output passes. Do not summarise — enumerate explicitly.
4. **DEBUG** — If verification fails or something breaks, check `patterns/INDEX.md` for a debug pattern. Follow it. Fix the issue and re-run VERIFY.
5. **GROW** — After meaningful work, run this binary checklist:
   - **Ground:** What changed in reality? Name the changed behavior, system, command, dependency, or workflow.
   - **Record:** If project state changed, update the "Current Project State" section above. If documented facts changed, update the relevant `context/` file surgically.
   - **Orient:** If this task can recur and no pattern exists, create one in `patterns/` using `patterns/README.md`, then add it to `patterns/INDEX.md`. If a pattern exists but you learned a gotcha, update it.
   - **Write:** Bump `last_updated` in every scaffold file you changed. If the why matters, run `mex log --type decision "<what changed and why>"` or `mex log "<note>"`.
