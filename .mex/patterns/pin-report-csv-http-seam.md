---
name: pin-report-csv-http-seam
description: Pinning download_data report CSV *content* (zip members, column sets, cell values, masking) at the HTTP seam in the unit lane, with hand-computed literals over a tiny factory timeline.
triggers:
  - "download_data CSV test"
  - "report zip content"
  - "CSV column set assertion"
  - "masked identifier download"
  - "report contents unit test"
edges:
  - target: "patterns/pin-raw-sql-builder.md"
    condition: "when pinning the raw-SQL builders behind the report instead of the HTTP seam"
  - target: "patterns/tenancy-and-caching.md"
    condition: "for the Organization-header / personal-workspace masking mechanics"
  - target: "patterns/run-tests-and-migrations.md"
    condition: "to run the unit lane / pre-commit"
last_updated: 2026-07-14
---

# Pin download_data Report CSV Content (HTTP seam)

## Context
`GET /api/v1/plios/{uuid}/download_data/` streams a zip of six CSVs plus a
README PDF, built by a raw-SQL + pandas pipeline in `plio/views.py`. Existing
`APITestCase` tests assert only the HTTP status. The plio unit fill (#375, slice
#401) pins the zip's *content* at the HTTP seam in the unit lane. This
**complements** the integration report journey
(`tests/integration/creator/test_report_contents.py`), which owns the unmasked
org-admin mcq path end-to-end and watch-time rounding — do not duplicate it.
Spec module: `tests/test_report_csv_contents.py` (outside `tests/integration/`).

## Steps
1. Build a deliberately tiny timeline with the shared factories in the **public
   schema** (personal workspace) — i.e. **no** `in_workspace(...)`, since a
   header-less download queries `public`. Objects land in `public` because the
   `db`/conftest fixtures reset the connection there.
2. Owner = a fresh `authed_client()`; the plio is `created_by=owner.user`,
   `published=True`. Seed a **decoy plio** in the same workspace with its own
   session/answer/event so every assertion proves the per-plio predicate held.
3. Download over the seam with **no** `organization=` (personal workspace ⇒ no
   org ⇒ the org-admin check is false ⇒ identifiers masked). Read the stream via
   `b"".join(response.streaming_content)` into `zipfile.ZipFile`.
4. Assert against **hand-computed literals**: zip `namelist()` set; each CSV's
   `csv.DictReader(...).fieldnames`; cell values selected by `question_type`.
5. Register a slice-local `report_dump_cleanup` fixture that `shutil.rmtree`s
   `/tmp/plio-<uuid>` — `download_data` only cleans its dump on the *next*
   download, so repeated local runs otherwise accumulate archives.

## Gotchas
- **download_data 500s for any plio with a subjective question.** The
  interaction-details step runs `question_correct_answer.apply(json.loads)` with
  **no null guard**, but a subjective question stores `correct_answer` as SQL
  NULL (`None` from the raw cursor) → `json.loads(None)` → `TypeError`. The
  responses step *does* null-guard its `answer` column; interaction-details does
  not. Existing status-only tests miss this (their plio has no questions). Fixing
  it is a product change (out of scope for the test-wall slices). Pin the desired
  subjective behaviour as a **`@pytest.mark.xfail(strict=True, reason=...)`**:
  it documents the spec and turns the build red if an upgrade/fix changes it.
- **Column order after the view's re-index shuffle.** The view drops `answer`
  from responses.csv and re-appends it, so `answer` is the **last** column.
  Interaction-details drops+re-appends `question_correct_answer` (already last).
  Enumerate headers from the SQL aliases *then* apply these moves.
- **List cells read back as their `str()` form.** A re-indexed checkbox answer
  `[0, 2]` → `[1, 3]` serializes as the string `"[1, 3]"` (space after comma);
  `csv.DictReader` strips the CSV quoting. A null answer → empty cell `""`,
  graded `is_answer_correct == "false"`.
- **Masking oracle:** Python `hashlib.md5(str(user.id).encode()).hexdigest()`,
  independent of Postgres `MD5(user_id::varchar)`. User-carrying CSVs are
  sessions, user-level-metrics, responses, events (not interaction-details /
  meta-details).
- Keep zip/CSV readers and the cleanup fixture **slice-local**; nothing goes into
  the shared harness until a second consumer appears.

## Verify
- [ ] Personal-workspace (no `organization=`) download → identifiers masked to `hashlib.md5`
- [ ] Every produced CSV proves decoy rows are absent
- [ ] Expected values are independent literals, never re-run through the app's own pipeline
- [ ] No `connection.set_schema()`; existing tests and product code untouched
- [ ] `docker-compose exec web pytest --ignore=tests/integration` green (xfail counts as pass)
- [ ] `pre-commit run --files tests/test_report_csv_contents.py` passes

## Debug
- Download 500 with `json.loads(None)` → the plio has a subjective question; that
  path is the known pre-existing bug — keep it under the strict xfail, don't
  "fix" the timeline by giving the subjective question a non-null correct_answer.
- Identifiers came back as emails, not MD5 → an `organization=` header leaked in,
  or the owner is (unexpectedly) an org admin of the default tenant.

## Update Scaffold
- [ ] Bump `last_updated` here if the mechanics change
- [ ] Add follow-up HTTP-seam report assertions to `tests/test_report_csv_contents.py`
