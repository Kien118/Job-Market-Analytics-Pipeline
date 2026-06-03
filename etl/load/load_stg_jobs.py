import os
from sqlalchemy import create_engine


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)


def load_stg_jobs(df):
    if df.empty:
        print("No transformed jobs to load.")
        return

    engine = create_engine(DATABASE_URL)

    df.to_sql(
        "stg_jobs",
        engine,
        if_exists="append",
        index=False
    )

    print(f"Loaded {len(df)} rows into stg_jobs")