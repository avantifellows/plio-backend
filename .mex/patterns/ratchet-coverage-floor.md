---
name: ratchet-coverage-floor
description: Measuring a lane's branch coverage and ratcheting its committed floor file up after a test-adding PR (the closing slice of every test-wall app fill).
triggers:
  - "ratchet coverage floor"
  - "bump coverage floor"
  - "coverage_floors"
  - "closing slice of a unit fill"
  - "lock in coverage gain"
edges:
  - target: "patterns/run-tests-and-migrations.md"
    condition: "to bring the stack up and run the lane"
  - target: "patterns/pin-raw-sql-builder.md"
    condition: "for the builder tests that produced the gain being locked in"
  - target: "patterns/pin-report-csv-http-seam.md"
    condition: "for the CSV-content tests that produced the gain being locked in"
last_updated: 2026-07-15
---

# Ratchet a Coverage Floor

## Context
Each lane (`unit`, `integration`) has a committed floor file in `coverage_floors/`
that CI fails under. Floors were seeded at **first-measured-minus-1%** (#382) and
**only ratchet up** — never lowered to make a build pass (#368). The closing slice
of every test-wall app fill (#375–#378) bumps its lane's floor to lock in the gain
the fill's tests produced, so a later change that deletes or weakens them fails CI.
Enforcement is in-repo (`scripts/check_coverage_floor.py`), not Codecov — Codecov's
upload died silently, so the floor is the real gate.

## Steps
1. Measure on the **merged state of all the fill's test slices** — measuring before
   they land ratchets against a stale baseline. Run the lane exactly as CI does:
   - unit: `docker-compose exec -T web coverage run -m pytest --ignore=tests/integration`
   - integration: `docker-compose exec -T web coverage run -m pytest -m integration`
2. Read the total: `docker-compose exec -T web coverage json -o coverage.json` then
   `python -c "import json;print(json.load(open('coverage.json'))['totals']['percent_covered'])"`.
   `.coveragerc` (branch on, app-scoped) is used automatically — do **not** edit it.
3. New floor = **measured − ~1%** (the #382 seeding margin; the #368 rule allows a
   0.5–1% band, so anything in `[measured−1, measured−0.5]` is valid). Round to 2 dp
   and keep the margin inside the band (e.g. measured 88.99 → 87.99, margin ≈0.997%).
4. The floor must be **≥ the current committed value** — if measured−margin does not
   exceed it, leave the floor unchanged and say so in the PR (never lower it).
5. Edit only the one lane's floor file (`coverage_floors/<lane>`); leave the other
   lane's floor untouched.
6. Verify the check passes at the new floor, including the base-branch ratchet guard:
   ```
   git show origin/<base-branch>:coverage_floors/<lane> > /tmp/base-floor-<lane>
   docker cp /tmp/base-floor-<lane> plio-backend-web-1:/tmp/base-floor-<lane>
   docker-compose exec -T web python scripts/check_coverage_floor.py \
     --lane <lane> --coverage-json coverage.json \
     --floor-file coverage_floors/<lane> --base-floor-file /tmp/base-floor-<lane>
   ```
   Exit 0 with "coverage meets the floor" and no ratchet-violation block.
7. State the measured value and the chosen floor in the PR description (or why the
   floor stayed put, if the gain fell inside the margin).

## Gotchas
- Expect a **modest gain** on assertion-depth fills: pre-existing status-code-only
  tests already *execute* the code, so newly-executed lines are few; the floor still
  ratchets per the rule.
- The CI ratchet guard compares against the **PR's base branch** floor, not `main` —
  raising the floor is always safe; the guard only fails on a missing/lowered file.
- Coverage is deterministic for a fixed test set on the same Python (3.8); the margin
  absorbs rounding, not flakiness — don't over-widen it.
- Keep the floor bump a **standalone slice**: no test, product, `.coveragerc`,
  floor-script, or CI-workflow changes ride along.

## Verify
- [ ] Lane green locally with the documented one-liner
- [ ] `coverage_floors/<lane>` = measured − 0.5–1%, ≥ the prior value, 2 dp
- [ ] The other lane's floor byte-identical to base
- [ ] `check_coverage_floor.py --lane <lane>` exits 0 with the base-floor guard
- [ ] PR description records measured value + chosen floor

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" when a lane's fill effort completes
- [ ] `mex log` the measured value and new floor when the rationale matters
