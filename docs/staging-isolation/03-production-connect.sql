-- SEPARATE PRODUCTION APPROVAL REQUIRED: review all legitimate DB clients first.
-- Observed owner/active role: postgres. Idle ETL/admin clients need inventory too.
-- Add explicit CONNECT grants for any other approved clients BEFORE the revoke.
BEGIN;
GRANT CONNECT ON DATABASE plio_production TO postgres;
REVOKE CONNECT ON DATABASE plio_production FROM PUBLIC;
REVOKE ALL PRIVILEGES ON DATABASE plio_production FROM plio_staging_app;
DO $$ BEGIN
  IF has_database_privilege('plio_staging_app', 'plio_production', 'CONNECT') THEN
    RAISE EXCEPTION 'Staging still inherits production CONNECT; rolling back';
  END IF;
END $$;
COMMIT;
-- Recheck template1/postgres and every other connectable database before enabling
-- the role. Restrict their PUBLIC grants only after inventorying their clients.
-- CONNECT revocation does not evict existing sessions: use a NEW role, not the
-- old shared login, and verify a fresh production connection is denied.
