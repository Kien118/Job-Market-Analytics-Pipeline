import os

from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)


def load_salary_summary(df):
    engine = create_engine(
        DATABASE_URL
    )

    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE mart_salary_summary"))

        if not df.empty:
            df.to_sql(
                "mart_salary_summary",
                connection,
                if_exists="append",
                index=False
            )

    print(
        f"Loaded {len(df)} salary rows"
    )
