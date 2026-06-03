import os

import pandas as pd

from sqlalchemy import create_engine


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)


def load_raw_jobs(jobs):
    if not jobs:
        print("No jobs extracted from API")
        return

    engine = create_engine(DATABASE_URL)

    df = pd.DataFrame(jobs)

    df.to_sql(
        "raw_jobs",
        engine,
        if_exists="append",
        index=False
    )

    print(f"Loaded {len(df)} jobs into raw_jobs")