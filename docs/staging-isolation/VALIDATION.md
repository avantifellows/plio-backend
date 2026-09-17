# Preparation checks — 2026-09-17

These checks validate the proposed change set, not live staging isolation.

- Unit lane, clean local test database: **330 passed, 1 xfailed**. Coverage 93.1%
  against the existing 92.15% floor. The expected failure remains visible.
- Integration lane, separate clean run: **133 passed, 1 skipped**. Disabled OTP
  cases verify 503/no new OTP and no consumption/user creation for an existing OTP.
- SNS publish uses a botocore stub: validates Transactional message attributes and
  fails if the removed account-wide settings call returns. No real SMS was sent.
- Credential-provider tests cover both session-token environment credentials and
  simulated ECS metadata credentials for SNS and S3. No real keys or AWS calls.
- Offline task-renderer tests reject production targets, wrong cache/database
  hosts, foreign secret/image paths, mutable image tags and environment files.
- Full pre-commit hooks: passed. `makemigrations --check --dry-run` for all eight
  application packages: no changes. No model, tenant-selection, cache invalidation
  or deletion semantics were changed; existing integration lanes cover header and
  default-tenant paths. No raw cache keys or hard-delete application code added.
- AWS IAM Access Analyzer `ValidatePolicy`: no findings for all five IAM/trust/S3
  policies. This read-only API did not create roles or install policies.
- IAM custom policy simulation: staging image PutObject allowed; production image
  PutObject/DeleteObject explicitly denied; SNS Publish explicitly denied.
  Resource policies/ACLs must still be checked during rollout; simulation is not
  proof of live isolation.
- Local PostgreSQL rehearsal using fresh disposable databases named plio_staging
  and plio_production: ownership generator transferred a schema, table, owned
  sequence and standalone sequence. New role could ALTER/INSERT and create a
  tenant schema; fresh production connection was denied after CONNECT changes.
  Rehearsal databases/role were removed afterwards. No remote database DDL ran.
- Read-only live metadata confirmed the current staging Fargate platform is 1.4.0
  and there are no container mounts; existing bucket ACLs grant only the owner
  FULL_CONTROL. Object-level ACL dependencies still require inventory.

Remaining before apply: code review/CI, production database client inventory,
public-ACL read dependency review, privately provisioned credentials and an exact
reviewed image digest. Live deployment, fresh denied connections under new real
credentials, storage/browser smoke and P03 recheck remain **NOT RUN**.

## Avatar review correction

Added the deployed `User.avatar_url` storage prefix (`avatars/`) alongside
`images/` in the staging task permissions, allowed listing prefixes, explicit
deny exclusions, and both public-read bucket policies. AWS Access Analyzer
returned no findings for the three changed policies. Sixteen IAM simulations
passed: Get/Put/Delete for both media prefixes are allowed on staging and
explicitly denied on production; listing both staging prefixes is allowed.
Both bucket policies still allow only anonymous GetObject, not public writes.
No live policies were installed.
