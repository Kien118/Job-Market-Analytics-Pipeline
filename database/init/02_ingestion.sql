\set ON_ERROR_STOP on

BEGIN;
LOCK TABLE public.raw_jobs IN ACCESS EXCLUSIVE MODE;
ALTER TABLE public.raw_jobs
    ADD COLUMN IF NOT EXISTS source_url TEXT,
    ADD COLUMN IF NOT EXISTS external_id TEXT,
    ADD COLUMN IF NOT EXISTS job_hash VARCHAR(32);

\ir functions/job_identity.sql

CREATE TABLE IF NOT EXISTS public.raw_jobs_identity_archive
    (LIKE public.raw_jobs, retained_job_id INTEGER NOT NULL, archived_at TIMESTAMPTZ NOT NULL DEFAULT now());

CREATE TEMP TABLE raw_identity_plan ON COMMIT DROP AS
WITH identities AS (
    SELECT job_id, public.job_identity(
        source, job_title, company_name, location, source_url, external_id
    ) AS identity_hash
    FROM public.raw_jobs
)
SELECT job_id, identity_hash, MIN(job_id) OVER (PARTITION BY identity_hash) AS retained_job_id
FROM identities;

INSERT INTO public.raw_jobs_identity_archive (
    job_id, source, job_title, company_name, location, salary_text, description,
    posted_date, source_url, external_id, job_hash, ingested_at, retained_job_id
)
SELECT raw.job_id, raw.source, raw.job_title, raw.company_name, raw.location,
       raw.salary_text, raw.description, raw.posted_date, raw.source_url,
       raw.external_id, raw.job_hash, raw.ingested_at, plan.retained_job_id
FROM public.raw_jobs AS raw
JOIN raw_identity_plan AS plan USING (job_id)
WHERE raw.job_id <> plan.retained_job_id;

DELETE FROM public.raw_jobs AS raw
USING raw_identity_plan AS plan
WHERE raw.job_id = plan.job_id AND raw.job_id <> plan.retained_job_id;

-- Clear changed keys first so an old unique key cannot block a different row's new key.
ALTER TABLE public.raw_jobs ALTER COLUMN job_hash DROP NOT NULL;
UPDATE public.raw_jobs AS raw SET job_hash = NULL
FROM raw_identity_plan AS plan
WHERE raw.job_id = plan.job_id AND raw.job_hash IS DISTINCT FROM plan.identity_hash;
UPDATE public.raw_jobs AS raw SET job_hash = plan.identity_hash
FROM raw_identity_plan AS plan
WHERE raw.job_id = plan.job_id AND raw.job_hash IS NULL;
UPDATE public.raw_jobs SET source = public.job_source_name(source)
WHERE source IS DISTINCT FROM public.job_source_name(source);
ALTER TABLE public.raw_jobs ALTER COLUMN job_hash SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS raw_jobs_job_hash_key ON public.raw_jobs (job_hash);
COMMIT;
