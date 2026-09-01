import hashlib
import math
import os

import pandas as pd
from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)


def normalize_hash_value(value):
    if value is None:
        return ""

    try:
        if math.isnan(value):
            return ""
    except (TypeError, ValueError):
        pass

    return str(value).strip().lower()


def generate_job_hash(
    source,
    job_title,
    company_name,
    location,
    source_url=None,
    external_id=None
):
    normalized_source_url = normalize_hash_value(source_url).rstrip("/")
    normalized_external_id = normalize_hash_value(external_id)

    if normalized_source_url:
        key = f"url|{normalized_source_url}"
    elif normalized_external_id:
        key = (
            f"external|{normalize_hash_value(source)}|"
            f"{normalized_external_id}"
        )
    else:
        key = (
            f"content|{normalize_hash_value(job_title)}|"
            f"{normalize_hash_value(company_name)}|"
            f"{normalize_hash_value(location)}"
        )

    return hashlib.md5(
        key.encode("utf-8")
    ).hexdigest()


def load_raw_jobs(jobs):
    if not jobs:
        print("No jobs extracted")
        return

    engine = create_engine(DATABASE_URL)

    df = pd.DataFrame(jobs)

    for column in ("source_url", "external_id"):
        if column not in df.columns:
            df[column] = None

    df = df.astype(object).where(pd.notna(df), None)

    df["job_hash"] = df.apply(
        lambda row: generate_job_hash(
            row.get("source"),
            row.get("job_title"),
            row.get("company_name"),
            row.get("location"),
            row.get("source_url"),
            row.get("external_id")
        ),
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
            source_url,
            external_id,
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
            :source_url,
            :external_id,
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
