import pandas as pd
from sqlalchemy import create_engine
import os


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/job_market_db"
)


def extract_raw_jobs():
    engine = create_engine(DATABASE_URL)

    query = """
        SELECT
            job_id,
            job_title,
            location,
            salary_text,
            description,
            posted_date
        FROM raw_jobs;
    """

    df = pd.read_sql(query, engine)

    return df