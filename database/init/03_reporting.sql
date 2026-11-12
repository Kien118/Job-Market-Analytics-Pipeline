\set ON_ERROR_STOP on
\set dashboard_password ''
\getenv dashboard_password DASHBOARD_DB_PASSWORD

BEGIN;
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'mart_salary_summary' AND column_name = 'location_name'
    ) THEN
        ALTER TABLE public.mart_salary_summary RENAME COLUMN location_name TO clean_location;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'mart_daily_job_stats' AND column_name = 'stat_date'
    ) THEN
        ALTER TABLE public.mart_daily_job_stats RENAME COLUMN stat_date TO posted_date;
    END IF;
END
$$;

ALTER TABLE public.stg_jobs
    ADD COLUMN IF NOT EXISTS source TEXT,
    ADD COLUMN IF NOT EXISTS posted_date DATE,
    ADD COLUMN IF NOT EXISTS ingested_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS salary_currency TEXT,
    ADD COLUMN IF NOT EXISTS salary_period TEXT,
    ADD COLUMN IF NOT EXISTS has_description BOOLEAN;
ALTER TABLE public.mart_salary_summary
    ADD COLUMN IF NOT EXISTS salary_currency TEXT,
    ADD COLUMN IF NOT EXISTS salary_period TEXT,
    ADD COLUMN IF NOT EXISTS sample_count INTEGER;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'job_market_dashboard') THEN
        CREATE ROLE job_market_dashboard NOLOGIN;
    END IF;
END
$$;

SELECT format('ALTER ROLE job_market_dashboard LOGIN PASSWORD %L', :'dashboard_password')
WHERE :'dashboard_password' <> '' \gexec

GRANT USAGE ON SCHEMA public TO job_market_dashboard;
GRANT SELECT ON public.stg_jobs TO job_market_dashboard;
COMMIT;
