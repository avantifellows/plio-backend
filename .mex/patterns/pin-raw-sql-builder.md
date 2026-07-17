---
name: pin-raw-sql-builder
description: Pinning a raw-SQL query builder (plio/queries.py) with a direct result-set test that runs the built SQL on a raw cursor over factory data and asserts hand-computed literals.
triggers:
  - "query builder test"
  - "raw SQL test"
  - "plio/queries.py"
  - "result-set assertion"
  - "download_data query"
edges:
  - target: "patterns/tenancy-and-caching.md"
    condition: "when the builder is schema-qualified and you need the tenancy mechanics"
  - target: "patterns/run-tests-and-migrations.md"
    condition: "to run the unit lane / pre-commit"
last_updated: 2026-07-15
---

# Pin a Raw-SQL Query Builder

## Context
`plio/queries.py` hand-writes schema-qualified SQL (f-strings) that the plio
viewset executes on a raw cursor for the metrics endpoint and the
`download_data` CSV zip. Existing tests execute these builders but never assert
their output, so a Django/psycopg bump can change a result set silently. The
plio unit fill (#375) pins each builder with a direct result-set test. All
builder tests live in one module: `tests/test_plio_queries.py` (unit lane —
outside `tests/integration/`). Slices #400–#404 append to it.

## Steps
1. Build a deliberately tiny timeline with the shared factories
   (`tests/factories.py`) **inside `in_workspace(org_a)`** (`tests/builders.py`).
2. Seed a **decoy plio** in the same workspace with its own session/answers/items
   so every assertion doubles as proof the per-plio predicate held.
3. Call the builder from `plio.queries`, passing the workspace schema explicitly
   (`org_a.schema_name`) — never `connection.set_schema()`.
4. Execute the returned SQL on a raw cursor via the slice-local `_run(query)`
   helper (`with connection.cursor() as cursor: cursor.execute(query); return
   cursor.fetchall()`). The SQL is fully schema-qualified, so it runs correctly
   even after the `in_workspace` block exits.
5. Assert the exact rows against **hand-computed literals** from the timeline.
   Builders with no `ORDER BY` → compare multisets (`Counter(rows) ==
   Counter([...])` — a `set` discards duplicates and hides join fan-out /
   `UNION ALL` regressions); builders with `ORDER BY` (user-level metrics) →
   assert the ordered list.

## Gotchas
- **jsonb reads back as its Postgres text form, not parsed Python.** A raw cursor
  returns `answer`/`options`/`correct_answer` as strings: scalar `0` → `"0"`,
  list `["A", "B"]` → `'["A", "B"]'` (note the space after the comma), stored
  NULL → `None`. Derive these from the jsonb text spec, not by copying output.
- `watch_time`/`item.time` are floats (`30.0`); `retention` is a str; `survey`
  is a bool; ids are ints. Reference created objects' `.id` (structural, e.g.
  rank-1 = the newer session) rather than hardcoding sequence values.
- The latest-responses builder has **two branches**: one session id → `WHERE
  session.id = <id>` (equality); many → `WHERE session.id IN (...)`. Discriminate
  with the substring `"session.id IN"` (plain `"IN"` also matches `INNER JOIN`).
- Masked identifier oracle (masking builders): Python `hashlib.md5` of the user
  id as a string — independent of Postgres `MD5`. The unmasked identifier
  coalesces email → mobile → unique_id.
- **Masking builders join `public.user`** (sessions dump, events, responses dump,
  user-level metrics), not just the tenant schema. Configure the identity matrix
  on the `UserFactory`: `UserFactory(email=None, ...)` drops down the coalesce;
  the `has_user_logged_in_via_sso` flag is `'true'` only when the user has **both**
  a `unique_id` *and* an `auth_org` (an Organization FK — pass `auth_org=org_a`),
  and `'false'` otherwise. One mobile-only learner with `unique_id`+`auth_org` set
  covers the coalesce-fallback and the SSO-`'true'` side at once.
- Keep the `_run` helper **slice-local** in the spec module; do not add it to the
  shared harness (`factories.py`, `builders.py`, `conftest.py`).
- **User-level-metrics `totalQuestions` reads the globally-max session id.** The
  builder derives the plio's question count from the single highest-id session
  (its documented "latest session for any user has the highest session_id"
  assumption), *not* a distinct count over the whole plio. So make the
  full-completion learner's session the **last-created** for that plio to fix
  `total_questions` at the full count, and drive the rewatch check by giving the
  rewatcher's *older* and *newer* sessions different items (older Q1; newer Q2+Q3)
  so a "counts both sessions" regression shows up as different attempted/correct
  numbers. This builder is the only one with an `ORDER BY` → assert the ordered
  list unmasked (emails sort predictably); for the masked run compare a multiset
  (`Counter`) since MD5 order is hash-dependent.
- **Subjective grading is safe at the builder seam.** `get_responses_dump_query`'s
  `is_answer_correct` CASE returns `'true'` for a non-null subjective answer with
  no problem — the `json.loads(None)` bug that 500s `download_data` for subjective
  questions lives in the pandas *interaction-details* step (pinned as a strict
  xfail at the HTTP seam by #401), not in the raw SQL. Pin the subjective grading
  outcome directly here.

## Verify
- [ ] Every test seeds a decoy and asserts its rows are absent
- [ ] Expected values are independent literals, never re-run through the app's own aggregation
- [ ] No `connection.set_schema()`; tenancy via `in_workspace(...)` + explicit schema arg
- [ ] `docker-compose exec web pytest --ignore=tests/integration` is green
- [ ] `pre-commit run --files tests/test_plio_queries.py` passes

## Debug
- Empty result set → the schema arg didn't match the workspace where factories
  wrote (must be `org_a.schema_name`), or the decoy filtering removed the target.
- jsonb literal mismatch → you asserted a parsed value (`0`, `["A", "B"]`)
  instead of the text form (`"0"`, `'["A", "B"]'`).

## Update Scaffold
- [ ] Bump `last_updated` here if the mechanics change
- [ ] Add follow-up builders to `tests/test_plio_queries.py`, not a new module
