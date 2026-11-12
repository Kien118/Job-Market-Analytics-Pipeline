BEGIN;

DO $$
DECLARE
    initial_id integer;
    replay_id integer;
    conflicting_id integer;
    replay_changed boolean;
    initial_timestamp timestamp;
BEGIN
    IF public.job_identity('TopDev Crawler', 'Engineer', 'Example', 'HCM',
            'https://TOPDEV.VN/detail-jobs/A/?src=topdev_home&medium=superhotjobs&job=42#share', NULL)
        IS DISTINCT FROM public.job_identity('TopDev', 'Other title', NULL, NULL,
            'https://topdev.vn/detail-jobs/A?job=42', NULL) THEN
        RAISE EXCEPTION 'Tracked TopDev URL did not match its canonical form';
    END IF;
    IF public.job_identity('TopDev', 'Engineer', 'Example', 'HCM', 'https://example.com/Jobs/A?job=42', NULL)
        = public.job_identity('TopDev', 'Engineer', 'Example', 'HCM', 'https://example.com/Jobs/A?job=43', NULL) THEN
        RAISE EXCEPTION 'A meaningful query parameter was dropped';
    END IF;
    IF public.job_identity('TopDev', 'Engineer', 'Example', 'HCM', 'https://example.com/Jobs/A', NULL)
        = public.job_identity('TopDev', 'Engineer', 'Example', 'HCM', 'https://example.com/jobs/a', NULL) THEN
        RAISE EXCEPTION 'Case-sensitive paths were merged';
    END IF;
    IF public.job_identity('CareerViet', 'Engineer', 'Example', 'HCM', NULL, NULL)
        = public.job_identity('TopDev', 'Engineer', 'Example', 'HCM', NULL, NULL) THEN
        RAISE EXCEPTION 'Fallback identity was not scoped to the source';
    END IF;

    SELECT job_id INTO STRICT initial_id
    FROM public.upsert_raw_job('fixture', 'Engineer', 'Example', 'HCM', '20 million', 'SQL',
        DATE '2026-01-01', 'https://example.com/a?utm_source=newsletter', 'fixture-job-42');

    SELECT ingested_at INTO STRICT initial_timestamp FROM public.raw_jobs WHERE job_id = initial_id;

    SELECT job_id, changed INTO STRICT replay_id, replay_changed
    FROM public.upsert_raw_job('fixture', 'Engineer', NULL, NULL, NULL, '', NULL,
        'https://example.com/a#fragment', 'fixture-job-42');
    IF replay_id <> initial_id OR replay_changed THEN
        RAISE EXCEPTION 'Unchanged replay produced a new or changed record';
    END IF;

    SELECT job_id, changed INTO STRICT replay_id, replay_changed
    FROM public.upsert_raw_job('fixture', 'Engineer', NULL, NULL, '30 million', NULL, NULL,
        'https://example.com/b', 'fixture-job-42');
    IF replay_id <> initial_id OR NOT replay_changed THEN
        RAISE EXCEPTION 'Update by external ID did not retain the existing row';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.raw_jobs
        WHERE job_id = initial_id AND description = 'SQL' AND salary_text = '30 million'
            AND source_url = 'https://example.com/b' AND ingested_at = initial_timestamp
    ) THEN
        RAISE EXCEPTION 'Update lost original fields or did not save the latest data';
    END IF;

    SELECT job_id INTO STRICT initial_id
    FROM public.upsert_raw_job('fixture', 'Engineer', 'Example', NULL, NULL, 'SQL', NULL,
        'https://example.com/promote?utm_source=newsletter', NULL);
    SELECT job_id, changed INTO STRICT replay_id, replay_changed
    FROM public.upsert_raw_job('fixture', 'Engineer', NULL, NULL, NULL, NULL, NULL,
        'https://example.com/promote', 'known-1');
    IF replay_id <> initial_id OR NOT replay_changed THEN
        RAISE EXCEPTION 'New external ID did not promote the URL-only row';
    END IF;
    SELECT job_id, changed INTO STRICT replay_id, replay_changed
    FROM public.upsert_raw_job('fixture', 'Engineer', NULL, NULL, NULL, NULL, NULL,
        'https://example.com/promote#fragment', NULL);
    IF replay_id <> initial_id OR replay_changed THEN
        RAISE EXCEPTION 'URL-only replay did not use the established external ID';
    END IF;
    SELECT job_id INTO STRICT conflicting_id
    FROM public.upsert_raw_job('fixture', 'Another Engineer', NULL, NULL, NULL, NULL, NULL,
        'https://example.com/promote', 'known-2');
    IF conflicting_id = initial_id OR NOT EXISTS (
        SELECT 1 FROM public.raw_jobs WHERE job_id = initial_id AND external_id = 'known-1' AND description = 'SQL'
    ) THEN
        RAISE EXCEPTION 'Listings with different known external IDs were merged';
    END IF;
END;
$$;

ROLLBACK;
