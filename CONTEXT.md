# Plio

Plio is an interactive video lesson platform: creators wrap a video with timed questions, learners watch and answer, and every workspace's data lives in its own Postgres schema. This context covers the backend API (this repo) and the vocabulary shared with the Vue frontend.

## Language

### Content

**Plio**:
An interactive video lesson — one video plus its timed questions — identified by a short uuid and owned by its creator inside one workspace.
_Avoid_: lesson, quiz, video (for the whole entity)

**Video**:
The YouTube video a plio wraps, stored as URL plus duration. A plio has exactly one.
_Avoid_: media, clip

**Item**:
A timed marker on a plio's video that pauses playback and presents an interaction. Today every item carries a question.
_Avoid_: marker, popup, interaction point

**Question**:
The interactive payload of an item — mcq, checkbox, or subjective — with optional image.
_Avoid_: prompt, exercise

### Tenancy

**Workspace**:
The user-facing name for a tenant: an organization with its own Postgres schema holding its plios and learner data. Every API request selects one via the `Organization` header.
_Avoid_: team, tenant (in product language)

**Organization**:
The model/record behind a workspace — shortcode, schema_name, api_key — living in the shared public schema. Use Organization for the model and header, Workspace in product language.
_Avoid_: company, client

**Personal workspace**:
The default schema a request lands in when no `Organization` header is sent (DEFAULT_TENANT_SHORTCODE); holds plios users create outside any organization.
_Avoid_: public workspace, default org

### People & auth

**Creator**:
A user who builds, publishes, and analyzes plios.
_Avoid_: teacher, author, admin

**Learner**:
A user who plays a plio and answers its questions — often entering through an org's SSO link rather than a Google login.
_Avoid_: student, viewer, end user

**Role**:
A user's named membership level inside one organization (e.g. org-admin); checked for workspace-scoped permissions.
_Avoid_: permission, group

**SSO login**:
Third-party entry: an organization authenticates a learner with its api_key plus the learner's unique_id, and the backend mints an internal token for a user scoped to that org (auth_org).
_Avoid_: external auth, api login

**Convert-token**:
The `/auth/convert-token/` exchange of a Google OAuth token for an internal OAuth token — the Google login path.
_Avoid_: social login endpoint, token swap

**OTP flow**:
Login by SMS one-time password (AWS SNS) against a mobile number.
_Avoid_: phone auth

### Learner runtime

**Session**:
One learner's continuous engagement with one plio. Reopening a plio creates a new session that carries over retention, answers, and last event from that learner's previous session on the same plio.
_Avoid_: attempt, visit, playthrough

**Session answer**:
A learner's answer to one item within a session — one row per item per session, carried forward on session creation.
_Avoid_: response, submission

**Event**:
A granular player interaction (play, pause, seek, answer) recorded within a session; the latest one is where a resumed learner picks up.
_Avoid_: log entry, action

### Test wall (decided vocabulary, map #362)

**Integration test**:
A backend API-journey test hitting the real Django app, tenant Postgres, and Redis — no browser. Lives in `tests/integration/`.
_Avoid_: API test, e2e (for backend suites)

**E2E journey**:
A browser test driving the full stack through one of the 9 inventoried user journeys (Playwright, plio-frontend).
_Avoid_: integration test (the frontend's old TestCafe specs are reclassified under e2e)

**Lane**:
One of the four test layers — frontend unit, backend unit, backend integration, e2e — each with its own CI job and coverage floor.
_Avoid_: suite (for the layer), stage

**Floor**:
The committed per-lane coverage minimum CI fails under; only moves up, bumped manually in the PR that adds tests.
_Avoid_: threshold, target

**Slow lane**:
The `slow_lane` pytest marker for the rare integration test that needs *committed* rows (the websocket canary) and so uses truncation-based cleanup instead of the suite's transaction rollback. Still blocks PRs; `pytest -m "integration and not slow_lane"` excludes it.
_Avoid_: nightly, commit test

## Relationships

- A **Plio** wraps one **Video** and contains ordered **Items**; each **Item** carries one **Question**
- A **Workspace** (an **Organization** with its own schema) holds its plios and learner data; Users and Organizations themselves live in the shared public schema
- The `Organization` request header picks the schema for every API call; no header lands in the **personal workspace**
- A **Session** belongs to one **Learner** and one **Plio**; **Session answers** (one per item) and **Events** belong to a session; a new session carries over from the learner's latest previous session on that plio
- An **SSO login** user is scoped to the **Organization** whose api_key created them (auth_org + unique_id)
- **Integration tests** cover API journeys and the tenancy/permission matrix; **E2E journeys** cover the 9 browser paths; each of the four **Lanes** enforces its own **Floor**

## Example dialogue

> **Dev:** "A learner closed the tab mid-video and reopened the plio — do we resume their session?"
> **Domain expert:** "We create a new **session** that carries over their answers, retention, and last **event** from the previous session on that **plio** — so the player resumes, but it's a new session row."

> **Dev:** "The same plio 404s when I fetch it with a different `Organization` header. Bug?"
> **Domain expert:** "No — plios live in the schema of the **workspace** they were created in. Wrong header, wrong schema. No header at all puts you in the **personal workspace**."

## Flagged ambiguities

- **Workspace vs Organization** — one entity, two names: Workspace is product language, Organization is the model, header, and tenant record. Pick by audience.
- **"plio"** names the product, the repo, the core Django app/package, *and* the entity. Qualify ("the plio app", "a plio") when it matters.
- **"Integration tests"** historically meant the frontend's TestCafe specs (`plio-frontend/tests/integration/`); the test-wall map reclassified those as e2e. On the backend, integration always means API-journey tests.
- **Item vs Question** — UI copy uses them interchangeably; the API does not (item = timed container, question = payload). Say which one you mean.
