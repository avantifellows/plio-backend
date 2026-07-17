# Coverage floors

One file per test lane, each holding a single number: the minimum branch
coverage percentage that lane must not drop below. CI (not Codecov) enforces
these via `scripts/check_coverage_floor.py` — a run whose measured coverage
falls under its lane's floor fails.

- `unit` — the backend unit lane (`pytest --ignore=tests/integration`)
- `integration` — the backend integration lane (`pytest -m integration`)

Floors were initialized at each lane's first measured value (branch coverage
on, source scoped by `.coveragerc`) minus one percent. They only ratchet
upward: when a PR pushes measured coverage more than ~2% above the floor, the
job summary nudges you to bump the floor here in that same PR so the gain is
locked in. Never lower a floor to make a red build pass.
