import pandas as pd


def extract_raw_jobs(connection):
    return pd.read_sql("""
        SELECT job_id, source, job_title, location, salary_text, description,
               posted_date, ingested_at
        FROM raw_jobs
    """, connection)
