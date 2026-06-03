import os

from sqlalchemy import create_engine


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)


def load_top_skills(df):

    if df.empty:
        print(
            "No skill data found"
        )
        return

    engine = create_engine(
        DATABASE_URL
    )

    df.to_sql(
        "mart_top_skills",
        engine,
        if_exists="replace",
        index=False
    )

    print(
        f"Loaded {len(df)} skills into mart_top_skills"
    )