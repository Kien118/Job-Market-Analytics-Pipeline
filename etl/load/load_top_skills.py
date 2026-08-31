import os

from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)


def load_top_skills(df):
    engine = create_engine(
        DATABASE_URL
    )

    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE mart_top_skills"))

        if not df.empty:
            df.to_sql(
                "mart_top_skills",
                connection,
                if_exists="append",
                index=False
            )

    print(
        f"Loaded {len(df)} skills into mart_top_skills"
    )
