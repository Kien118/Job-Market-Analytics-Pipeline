import os
from datetime import date, datetime

from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)

JOB_FIELDS = (
    "source", "job_title", "company_name", "location", "salary_text",
    "description", "posted_date", "source_url", "external_id",
)

UPSERT_JOB = text("""
    SELECT job_id, changed FROM public.upsert_raw_job(
        :source, :job_title, :company_name, :location, :salary_text,
        :description, :posted_date, :source_url, :external_id
    )
""")


def validated_job(job):
    if not isinstance(job, dict):
        raise ValueError("job must be an object")
    row = {field: job.get(field) for field in JOB_FIELDS}
    for field, value in row.items():
        if value is None:
            continue
        if field == "posted_date":
            if not isinstance(value, date) or isinstance(value, datetime):
                raise ValueError("posted_date must be a date")
        elif not isinstance(value, str) or "\0" in value:
            raise ValueError(f"{field} must be text without null bytes")

    if not row["source"] or not row["source"].strip() or len(row["source"].strip()) > 100:
        raise ValueError("source must have between 1 and 100 characters")
    if not row["job_title"] or not row["job_title"].strip():
        raise ValueError("job_title is required")
    return row


def load_raw_jobs(jobs):
    rows = [validated_job(job) for job in jobs]
    if not rows:
        return {"written": 0, "unchanged": 0}

    engine = create_engine(DATABASE_URL)
    try:
        with engine.begin() as connection:
            written = sum(
                connection.execute(UPSERT_JOB, row).one().changed for row in rows
            )
    finally:
        engine.dispose()

    return {"written": written, "unchanged": len(rows) - written}
