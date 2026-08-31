import os
from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)


def load_stg_jobs(df):
    engine = create_engine(DATABASE_URL)

    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE stg_jobs"))

        if not df.empty:
            df.to_sql(
                "stg_jobs",
                connection,
                if_exists="append",
                index=False
            )

    print(f"Loaded {len(df)} rows into stg_jobs")
