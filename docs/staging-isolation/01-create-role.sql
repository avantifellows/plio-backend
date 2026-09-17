-- REVIEW ONLY: role is initially unable to log in. Run as the RDS administrator.
-- This is not an application migration and is never run by entrypoint.sh.
CREATE ROLE plio_staging_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOINHERIT NOREPLICATION NOBYPASSRLS;
-- RDS postgres is not a true superuser: it needs membership in the NEW owner
-- for ALTER ... OWNER. This direction does NOT give the app postgres privileges.
GRANT plio_staging_app TO postgres;
GRANT CONNECT, CREATE, TEMPORARY ON DATABASE plio_staging TO plio_staging_app;
-- Supply a unique password privately using psql \password plio_staging_app.
-- Do NOT activate LOGIN until production CONNECT restrictions are verified.
