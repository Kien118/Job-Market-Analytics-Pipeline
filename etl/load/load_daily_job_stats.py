import os

from sqlalchemy import create_engine


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)


def load_daily_job_stats(df):
    if df.empty:
        print("No daily job stats data")
        return

    engine = create_engine(DATABASE_URL)

    df.to_sql(
        "mart_daily_job_stats",
        engine,
        if_exists="replace",
        index=False
    )

    print(f"Loaded {len(df)} daily job stats rows")