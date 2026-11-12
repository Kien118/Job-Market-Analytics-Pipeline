CREATE TABLE IF NOT EXISTS public.ingestion_runs (
    run_id UUID NOT NULL,
    source TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    succeeded BOOLEAN NOT NULL,
    result JSONB NOT NULL,
    PRIMARY KEY (run_id, source)
);
