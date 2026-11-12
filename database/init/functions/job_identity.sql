CREATE OR REPLACE FUNCTION public.job_source_key(value text)
RETURNS text
LANGUAGE sql IMMUTABLE
AS $$
    SELECT CASE lower(btrim(value))
        WHEN 'careerviet crawler' THEN 'careerviet'
        WHEN 'topdev crawler' THEN 'topdev'
        ELSE lower(btrim(value))
    END
$$;

CREATE OR REPLACE FUNCTION public.job_source_name(value text)
RETURNS text
LANGUAGE sql IMMUTABLE
AS $$
    SELECT CASE public.job_source_key(value)
        WHEN 'careerviet' THEN 'CareerViet'
        WHEN 'topdev' THEN 'TopDev'
        WHEN 'arbeitnow' THEN 'Arbeitnow'
        ELSE btrim(value)
    END
$$;

CREATE OR REPLACE FUNCTION public.canonical_job_url(source text, source_url text)
RETURNS text
LANGUAGE sql IMMUTABLE
AS $$
    WITH url AS (
        SELECT regexp_match(btrim(source_url), '^(https?://[^/?#]+)([^?#]*)(?:[?]([^#]*))?(?:#.*)?$', 'i') AS parts
    )
    SELECT lower(parts[1]) || rtrim(parts[2], '/') || coalesce(
        '?' || (
            SELECT string_agg(parameter, '&' ORDER BY position)
            FROM unnest(string_to_array(parts[3], '&')) WITH ORDINALITY AS query(parameter, position)
            WHERE parameter <> ''
              AND split_part(parameter, '=', 1) !~* '^utm_'
              AND lower(split_part(parameter, '=', 1)) NOT IN ('fbclid', 'gclid', 'msclkid')
              AND NOT (
                  public.job_source_key(source) IS NOT DISTINCT FROM 'topdev'
                  AND lower(split_part(parameter, '=', 1)) IN ('src', 'medium')
              )
        ),
        ''
    )
    FROM url
$$;

CREATE OR REPLACE FUNCTION public.job_identity(
    source text, job_title text, company_name text, location text, source_url text, external_id text
)
RETURNS text
LANGUAGE sql IMMUTABLE
AS $$
    SELECT md5(
        CASE
            WHEN nullif(btrim(external_id), '') IS NOT NULL THEN
                jsonb_build_array('id', public.job_source_key(source), btrim(external_id))
            WHEN public.canonical_job_url(source, source_url) IS NOT NULL THEN
                jsonb_build_array('url', public.job_source_key(source), public.canonical_job_url(source, source_url))
            ELSE
                jsonb_build_array(
                    'content', public.job_source_key(source), lower(btrim(job_title)),
                    nullif(lower(btrim(company_name)), ''), nullif(lower(btrim(location)), '')
                )
        END::text
    )
$$;

CREATE INDEX IF NOT EXISTS raw_jobs_known_id_url_idx ON public.raw_jobs (
    public.job_source_key(source), public.canonical_job_url(source, source_url)
) WHERE source_url IS NOT NULL AND external_id IS NOT NULL;

CREATE OR REPLACE FUNCTION public.upsert_raw_job(
    p_source text, p_job_title text, p_company_name text, p_location text, p_salary_text text,
    p_description text, p_posted_date date, p_source_url text, p_external_id text
)
RETURNS TABLE (job_id integer, changed boolean)
LANGUAGE plpgsql
AS $$
DECLARE
    identity_hash text := public.job_identity(p_source, p_job_title, p_company_name, p_location, p_source_url, p_external_id);
    canonical_url text := public.canonical_job_url(p_source, p_source_url);
    source_key text := public.job_source_key(p_source);
    external_key text := nullif(btrim(p_external_id), '');
    url_identity_hash text;
    known_hashes text[];
    saved_job_id integer;
BEGIN
    IF nullif(btrim(p_source), '') IS NULL OR nullif(btrim(p_job_title), '') IS NULL THEN
        RAISE EXCEPTION 'source and job title are required' USING ERRCODE = '23514';
    END IF;

    -- Lock this source so URL-only and ID-bearing writes cannot race during promotion.
    PERFORM pg_advisory_xact_lock(hashtextextended('public.upsert_raw_job:' || source_key, 0));
    IF canonical_url IS NOT NULL THEN
        SELECT ARRAY(
            SELECT saved.job_hash
            FROM public.raw_jobs AS saved
            WHERE saved.source_url IS NOT NULL AND saved.external_id IS NOT NULL
              AND btrim(saved.external_id) <> ''
              AND public.job_source_key(saved.source) = source_key
              AND public.canonical_job_url(saved.source, saved.source_url) = canonical_url
            LIMIT 2
        ) INTO known_hashes;

        IF external_key IS NULL AND cardinality(known_hashes) = 1 THEN
            identity_hash := known_hashes[1];
        ELSIF external_key IS NOT NULL AND cardinality(known_hashes) = 0 THEN
            url_identity_hash := public.job_identity(p_source, NULL, NULL, NULL, canonical_url, NULL);
            UPDATE public.raw_jobs AS saved SET job_hash = identity_hash
            WHERE saved.job_hash = url_identity_hash
              AND nullif(btrim(saved.external_id), '') IS NULL
              AND NOT EXISTS (SELECT 1 FROM public.raw_jobs AS identified WHERE identified.job_hash = identity_hash);
        END IF;
    END IF;

    INSERT INTO public.raw_jobs AS saved (
        source, job_title, company_name, location, salary_text, description, posted_date,
        source_url, external_id, job_hash
    )
    VALUES (
        public.job_source_name(p_source), btrim(p_job_title), nullif(btrim(p_company_name), ''), nullif(btrim(p_location), ''),
        nullif(btrim(p_salary_text), ''), nullif(btrim(p_description), ''), p_posted_date,
        canonical_url, external_key, identity_hash
    )
    ON CONFLICT (job_hash) DO UPDATE SET
        job_title = excluded.job_title,
        company_name = coalesce(excluded.company_name, saved.company_name),
        location = coalesce(excluded.location, saved.location),
        salary_text = coalesce(excluded.salary_text, saved.salary_text),
        description = coalesce(excluded.description, saved.description),
        posted_date = coalesce(excluded.posted_date, saved.posted_date),
        source_url = coalesce(excluded.source_url, saved.source_url),
        external_id = coalesce(excluded.external_id, saved.external_id)
    WHERE (saved.job_title, saved.company_name, saved.location, saved.salary_text,
           saved.description, saved.posted_date, saved.source_url, saved.external_id)
        IS DISTINCT FROM (
            excluded.job_title, coalesce(excluded.company_name, saved.company_name),
            coalesce(excluded.location, saved.location), coalesce(excluded.salary_text, saved.salary_text),
            coalesce(excluded.description, saved.description), coalesce(excluded.posted_date, saved.posted_date),
            coalesce(excluded.source_url, saved.source_url), coalesce(excluded.external_id, saved.external_id)
        )
    RETURNING saved.job_id INTO saved_job_id;

    IF FOUND THEN
        RETURN QUERY SELECT saved_job_id, true;
    ELSE
        RETURN QUERY SELECT saved.job_id, false FROM public.raw_jobs AS saved WHERE saved.job_hash = identity_hash;
    END IF;
END;
$$;
