---
name: run-tests-and-migrations
description: Running the test suite and handling migrations in the dockerized dev environment, including soft-delete and tenancy wrinkles.
triggers:
  - "run tests"
  - "test suite"
  - "migration"
  - "makemigrations"
  - "migrate"
edges:
  - target: "context/setup.md"
    condition: "if the docker environment isn't up yet"
last_updated: 2026-07-13
---

# Run Tests & Migrations

## Context
The supported environment is docker compose (services: db, web, redis). Legacy Django/DRF
tests (`APITestCase`) and plain integration specs share pytest. CI runs separate unit and
integration lanes on Python 3.8; the unit lane retains the existing Codecov upload.

## Steps
1. Ensure the stack is up: `docker-compose up -d --build`
2. Unit suite: `docker-compose exec web pytest --ignore=tests/integration`
3. Integration lane: `docker-compose exec web pytest -m integration`
4. One app or case: `docker-compose exec web pytest users/tests.py` (or a pytest node id)
5. Migrations: `docker-compose exec web python manage.py makemigrations` → inspect the generated files → `docker-compose exec web python manage.py migrate`
6. Before committing: `pre-commit run --all-files`

## Gotchas
- makemigrations with no model changes can still emit migrations if a third-party package (notably django-safedelete) changes model state between versions — treat unexpected migrations as a red flag, not noise
- Tenant apps migrate per schema — a migration that's instant on the public schema multiplies across every workspace schema in production
- Image-related tests use a local-storage mixin so S3 isn't hit — don't add tests that require real AWS credentials
- Silk profiling middleware is active in local settings; it can distort timing-sensitive assertions

## Verify
- [ ] Full suite green locally before pushing (CI mirrors it with coverage)
- [ ] `makemigrations` after your change emits nothing unexpected (run it once more to confirm a clean state)
- [ ] pre-commit hooks pass

## Debug
- Tests can't connect to db/redis → containers not up, or env points at localhost instead of the compose service names (`db`, `redis`)
- A "random" migration appears for an app you didn't touch → diff the package versions first (safedelete is the usual suspect)
- Auth-dependent tests failing en masse → the test OAuth application setup didn't run; check `DEFAULT_OAUTH2_CLIENT_SETUP` handling in test settings

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" if what's working/not built has changed
- [ ] Update any `.mex/context/` files that are now out of date
- [ ] If this is a new task type without a pattern, create one in `.mex/patterns/` and add to `INDEX.md`
