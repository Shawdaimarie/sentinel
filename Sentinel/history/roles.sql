-- Run as the migration owner after migrations. These groups cannot log in.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sentinel_history_reader') THEN
        CREATE ROLE sentinel_history_reader NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sentinel_history_writer') THEN
        CREATE ROLE sentinel_history_writer NOLOGIN;
    END IF;
END $$;
GRANT USAGE ON SCHEMA sentinel_history TO sentinel_history_reader, sentinel_history_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA sentinel_history
    TO sentinel_history_reader, sentinel_history_writer;
GRANT INSERT ON sentinel_history.suites, sentinel_history.sources, sentinel_history.cases,
    sentinel_history.runs, sentinel_history.metrics, sentinel_history.tags,
    sentinel_history.comparisons, sentinel_history.regressions TO sentinel_history_writer;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA sentinel_history TO sentinel_history_writer;
-- Grant these groups to separate login roles; never grant the reader the writer group.
-- Owner-only: DDL, migration records, UPDATE, DELETE, TRUNCATE and retention operations.
