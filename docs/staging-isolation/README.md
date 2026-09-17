# Staging isolation rollout — prepared, not applied

This change set follows [P03 in #443](https://github.com/avantifellows/plio-backend/issues/443).
Merging the PR does **not** isolate staging: the database, bucket policies and
ECS configuration below must also be applied and verified. Do not run acceptance
writes until that gate is met. There is no automatic infrastructure apply hook.

## Observed baseline (2026-09-17)

- Backend main/staging: `430ed6b`, task definition `plio-backend-staging:254`.
- RDS PostgreSQL 16.13: `plio_staging` and `plio_production` share an instance and
  the `postgres` login. Both database ACLs are currently default (PUBLIC CONNECT).
- Staging non-system objects: 16 schemas, 255 tables, 252 sequences, all owned by
  `postgres`. Production ownership is not to be transferred.
- Both task roles/execution roles currently use `ecsTaskExecutionRole`; the apps
  receive shared static root AWS credentials. Do not copy them into artifacts.
- The serving staging task uses Fargate 1.4.0 / awsvpc with no mounts, supporting
  the planned JSON-key secret injection. Recheck before applying a new revision.
- Buckets `plio-staging-assets` and `plio-prod-assets` allow anonymous image
  writes/deletes. Bucket ACLs have only owner FULL_CONTROL; object ACLs were not
  enumerated. Both lack ownership controls. Public image URLs are intentional in
  the current application (`AWS_QUERYSTRING_AUTH=False`).
- No committed Terraform/CloudFormation was found. These are explicit reviewed
  policy documents and operator steps, not a new infrastructure framework.

Refresh this baseline before applying. Any drift requires reviewing the delta.

## 1. Application behavior in this PR

- SNS obtains credentials through the SDK chain (including ECS role/session
  credentials) and marks each message Transactional. It no longer changes the
  AWS account's default SMS settings on every send.
- `SMS_DRIVER=disabled` returns 503 for request/verify OTP without creating or
  consuming OTPs. Existing `sns` and development unset behavior is preserved.
- `FRONTEND_URL` can be configured; production remains the default. Repository
  search found no application call sites today, so this setting alone does not
  fix or verify OAuth callbacks. Check provider settings and actual browser login.
- Existing uploads continue to use the SDK-compatible django-storages backend.

## 2. Database change (operator review required)

First inventory all legitimate DB clients, including idle ETL/admin tools not
visible in current sessions. Capture grants/owners and a staging backup privately.
Pause staging writes/deployments during ownership transfer. No production data
copy, data deletion, broad REASSIGN OWNED or production ownership change is needed.

1. Review/run `01-create-role.sql` as the DB administrator. It creates a role
   that cannot log in yet. Set a unique password privately with psql `\password`;
   store `{username,password}` in Secrets Manager `plio/staging/database` using
   the AWS-managed Secrets Manager key. Never pass a password on a command line.
2. Generate staging-only ownership statements with
   `psql -X -qAt -v ON_ERROR_STOP=1 -d plio_staging -f docs/staging-isolation/02-preview-staging-ownership.sql`.
   Use private connection settings, not a credential-bearing command/URL.
   Inspect the output against current catalog counts, including any views,
   functions, types or extensions outside the observed baseline. Stop on drift.
   The generator only emits SQL; save/review it before running it as administrator.
   It transfers staging schemas/tables and standalone sequences, not the database
   or cluster-wide objects. The app role needs staging CREATE for tenant schemas.
3. **Separate production access change:** review `03-production-connect.sql`.
   Grant every legitimate production client CONNECT explicitly before removing
   PUBLIC CONNECT. The observed owner `postgres` is retained, but current sessions
   alone do not prove the full client inventory. No production rows are queried.
4. Audit other databases (including `postgres`/`template1`), PUBLIC schema grants,
   executable SECURITY DEFINER functions, role membership and extension access.
   Restrict unneeded database CONNECT through separately reviewed grants; do not
   leave the new role a route to administrative objects on the shared instance.
5. Assert the new role has no administrative capabilities/memberships and
   `has_database_privilege('plio_staging_app','plio_production','CONNECT')` is false.
   Enable LOGIN only after those checks, then verify a **fresh** production
   connection using the new credential is denied. Do not test production writes.
6. Apply the reviewed staging ownership statements and prove startup migrations,
   bootstrap commands and tenant creation with the new role. Use a disposable
   LOCAL fixture for the initial rehearsal; live staging writes follow P03 approval.

The lean first rollout uses one staging-only owner/login because startup currently
runs DDL. A separate migrator/runtime split can follow; never grant cluster-wide
CREATEDB/CREATEROLE just to make startup work.

## 3. AWS roles and buckets

Create `plio-backend-staging-app` with `staging-task-trust.json` and
`staging-task-policy.json`. The explicit S3 deny prevents authenticated access
outside the staging image/avatar resources even where a bucket policy is public. SMS is
explicitly denied until controlled delivery is ready.

Create `plio-backend-staging-execution` with the same ECS trust, AWS's managed
`AmazonECSTaskExecutionRolePolicy`, and `staging-execution-policy.json`. This
permits injection of only the named staging DB secret (six-character AWS suffix).
If a customer-managed KMS key is used instead, separately review a key-specific
Decrypt grant; do not add wildcard KMS or secret access. Confirm the service's
Fargate platform/agent supports JSON-key secret injection before rollout.

Apply `staging-bucket-policy.json` to staging after comparing the live policy.
It retains public lesson-image and avatar reads; authenticated task-role IAM grants permit writes.
The production counterpart is a **separate reviewed policy change**, after proving
the production upload principal has its own Get/Put/Delete permissions.

Review and apply `public-access-block.json` per bucket: ignore/block public ACLs
while retaining intentional policy-based public reads. First inspect whether any
legitimate assets outside `images/` and `avatars/` rely on public ACLs. Do not silently break
them; migrate that read access before applying. These files must not overwrite
new legitimate policy statements introduced after this baseline.

Validate policy syntax with IAM Access Analyzer. Evaluate denied production
access using IAM simulation plus resource-policy/ACL inspection, not writes to
production. IAM simulation alone does not establish effective live access.
After isolation, a disposable staging image verifies authenticated upload, read,
replace and supported cleanup; repeat with a disposable avatar. Unsigned browser
reads for both existing images and avatars must still work. Never use
an anonymous destructive request against an existing object as a denial test.

Root-key retirement is a follow-up after ALL consumers, including production and
GitHub deployment workflows, have moved off it. This rollout removes it from
staging; it does not disable production's current key or alter production deploys.

## 4. Prepare ECS revision without deploying

Use a private directory (`umask 077`) for all task-definition files: unrelated
existing secrets may still appear in them. Do not attach them to the PR.

1. Build the reviewed PR image through the approved staging release process and
   record its ECR digest. Do not deploy the old image with `SMS_DRIVER=disabled`:
   old code would treat that value as development/no-send mode.
2. Read the CURRENT SERVING task definition from the service, not the family
   latest revision. Save it privately. Inspect mounts/entrypoint/sidecars for
   other credential sources. This baseline has one application container.
3. Render offline (substitute the newly created secret ARN and reviewed digest):

   ```sh
   python scripts/prepare_staging_task.py \
     --input /private/path/current-task.json \
     --output /private/path/proposed-task.json \
     --db-secret-arn "$STAGING_DB_SECRET_ARN" \
     --image "$STAGING_REVIEWED_IMAGE"
   ```

   The tool refuses production family/configuration, foreign secret/image paths,
   mutable image tags, sidecars and environment files. It removes inline DB/AWS
   credentials, adds DB secret references, assigns separate roles, sets staging
   frontend origin and disables SMS. It calls no AWS API and outputs no secrets.
4. Review a sanitized diff. Preserve service network/log/CPU/memory settings.
   Register only after approval, using `aws ecs register-task-definition` with
   the private input file. Update ONLY `plio-staging-cluster` /
   `plio-backend-staging` to the reviewed resulting revision.
5. Freeze stale deployment runs during cutover. The existing workflow reads the
   latest family revision, so check its inputs before later approvals; an old
   queued run must not overwrite the new image/configuration. Audit retained
   revisions; never use a root-credential revision as a rollback candidate.

## 5. Release checks and rollback

- Verify serving image digest, database username and assumed-role identity without
  printing passwords, keys or session credentials. Confirm production is unchanged.
- Re-run P01/P02: startup/migrations, docs/static assets, login page, safe errors,
  expected redirects, target health and correlated logs. Confirm disabled OTP
  returns 503 and creates no OTP; do not claim SMS delivery passes.
- Re-run P03: fresh production DB connection denied, no admin memberships, storage
  writes restricted, existing image reads preserved, separate Redis unchanged.
- Resolve telemetry handling and arrange P04 run-owned accounts/workspaces. A
  shared telemetry project requires an explicit accepted environment/PII policy;
  no analytics mocking to manufacture a clean browser result.
- After permission checks pass, use real browser login, lesson/image creation,
  learner answers and reloads; retain screenshots/network evidence. SMS and webhook
  tests remain blocked until controlled recipients are available.
- Roll back code only with the new isolated configuration. A known-good image
  must support disabled SMS; otherwise keep staging paused rather than restoring
  root/shared credentials. For a permission defect, repair the scoped grant or
  use the preserved staging-only owner/deploy path. Never restore public writes.
- Ownership changes are transactional with a five-second lock timeout. Keep the
  captured ownership map for a separately reviewed reversal if needed; do not use
  broad cluster-level reassignment. No production restore is part of rollback.

## Evidence and remaining operator decisions

Before apply: record policy validation, local DB ownership rehearsal, test/CI
results, legitimate production DB clients, public-ACL read dependencies, deployment
agent secret support, exact reviewed image and secret ARN. Those last inventory
items cannot be inferred from a green unit test. Network ingress tightening and
full root-key retirement need separate production-aware rollouts.

References: [ECS task roles](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html),
[PostgreSQL 16 privilege revocation](https://www.postgresql.org/docs/16/sql-revoke.html),
[S3 public-access settings](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html),
[Boto3 credential chain](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html).
