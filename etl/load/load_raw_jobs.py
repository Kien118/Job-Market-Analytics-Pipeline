import hashlib
import os

import pandas as pd
from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)


def generate_job_hash(row):
    key = (
        f"{row.get('job_title', '')}|"
        f"{row.get('company_name', '')}|"
        f"{row.get('location', '')}"
    )

    return hashlib.md5(
        key.lower().strip().encode("utf-8")
    ).hexdigest()


def load_raw_jobs(jobs):
    if not jobs:
        print("No jobs extracted")
        return

    engine = create_engine(DATABASE_URL)

    df = pd.DataFrame(jobs)

    df["job_hash"] = df.apply(
        generate_job_hash,
        axis=1
    )

    inserted_count = 0
    skipped_count = 0

    insert_sql = text("""
        INSERT INTO raw_jobs (
            source,
            job_title,
            company_name,
            location,
            salary_text,
            description,
            posted_date,
            job_hash
        )
        VALUES (
            :source,
            :job_title,
            :company_name,
            :location,
            :salary_text,
            :description,
            :posted_date,
            :job_hash
        )
        ON CONFLICT (job_hash) DO NOTHING;
    """)

    with engine.begin() as conn:
        for job in df.to_dict(orient="records"):
            result = conn.execute(
                insert_sql,
                job
            )

            if result.rowcount == 1:
                inserted_count += 1
            else:
                skipped_count += 1

    print(f"Inserted {inserted_count} new jobs into raw_jobs")
    print(f"Skipped {skipped_count} duplicate jobs")