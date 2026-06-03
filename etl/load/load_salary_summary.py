import os

from sqlalchemy import create_engine


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)


def load_salary_summary(df):

    if df.empty:

        print(
            "No salary data available"
        )

        return

    engine = create_engine(
        DATABASE_URL
    )

    df.to_sql(
        "mart_salary_summary",
        engine,
        if_exists="replace",
        index=False
    )

    print(
        f"Loaded {len(df)} salary rows"
    )