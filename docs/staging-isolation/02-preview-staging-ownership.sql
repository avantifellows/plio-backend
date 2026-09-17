-- READ-ONLY GENERATOR. Run with psql -X -qAt -v ON_ERROR_STOP=1 on plio_staging.
-- Save the output privately, inspect it, then apply only after approval.
-- Never replace this with REASSIGN OWNED (which also affects shared objects).
DO $$ BEGIN
  IF current_database() <> 'plio_staging' THEN
    RAISE EXCEPTION 'Expected plio_staging; no ownership plan generated';
  END IF;
END $$;
SELECT 'BEGIN;';
SELECT 'SET LOCAL lock_timeout = ''5s'';';
SELECT 'DO $$ BEGIN IF current_database() <> ''plio_staging'' THEN RAISE EXCEPTION ''Wrong database''; END IF; END $$;';
SELECT format('ALTER SCHEMA %I OWNER TO plio_staging_app;', nspname)
FROM pg_namespace
WHERE nspname !~ '^pg_' AND nspname <> 'information_schema'
  AND nspowner = 'postgres'::regrole
ORDER BY nspname;
SELECT format('ALTER TABLE %I.%I OWNER TO plio_staging_app;', n.nspname, c.relname)
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
  AND c.relkind IN ('r', 'p') AND c.relowner = 'postgres'::regrole
  AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass
    AND d.objid = c.oid AND d.deptype = 'e')
ORDER BY n.nspname, c.relname;
-- Table ownership also transfers its owned sequences; standalone ones follow.
SELECT format('ALTER SEQUENCE %I.%I OWNER TO plio_staging_app;', n.nspname, c.relname)
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'
  AND c.relkind = 'S' AND c.relowner = 'postgres'::regrole
  AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass
    AND d.objid = c.oid AND d.deptype IN ('a', 'i', 'e'))
ORDER BY n.nspname, c.relname;
SELECT 'COMMIT;';
