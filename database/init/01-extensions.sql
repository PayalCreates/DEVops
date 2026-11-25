-- Runs once, on first start of an empty PostgreSQL volume.
-- The schema itself is owned by Alembic migrations (apps/backend/migrations);
-- this file only prepares database-level settings.

-- pg_stat_statements: query statistics used during bottleneck analysis.
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Fail fast instead of hanging on locks or runaway queries.
DO $$
BEGIN
  EXECUTE format('ALTER DATABASE %I SET statement_timeout = %L', current_database(), '30s');
  EXECUTE format('ALTER DATABASE %I SET lock_timeout = %L', current_database(), '10s');
  EXECUTE format('ALTER DATABASE %I SET idle_in_transaction_session_timeout = %L',
                 current_database(), '60s');
END
$$;
