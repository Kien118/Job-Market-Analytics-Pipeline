import logging
import os

from sqlalchemy import create_engine, text

from analytics.build_daily_job_stats import build_daily_job_stats
from analytics.build_salary_summary import build_salary_summary
from analytics.build_top_skills import build_top_skills
from extract.extract_raw_jobs import extract_raw_jobs
from quality.quality_checks import log_coverage, validate_analytics
from transform.transform_jobs import transform_jobs


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_pipeline():
    engine = create_engine(
        os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/job_market_db"),
        isolation_level="READ COMMITTED",
        hide_parameters=True,
    )
    step = "read source data"
    try:
        with engine.begin() as connection:
            # Serialize refreshes before reading so an older snapshot cannot overwrite a newer one.
            connection.execute(text("SELECT pg_advisory_xact_lock(hashtext('job_market.publish_analytics'))"))
            raw = extract_raw_jobs(connection)
            logger.info("Extracted %d raw jobs", len(raw))
            if raw.empty and connection.scalar(text("""
                SELECT EXISTS (
                    SELECT 1 FROM stg_jobs UNION ALL
                    SELECT 1 FROM mart_top_skills UNION ALL
                    SELECT 1 FROM mart_salary_summary UNION ALL
                    SELECT 1 FROM mart_daily_job_stats
                )
            """)):
                raise ValueError("Raw data is empty while published tables contain data")

            step = "transform and validate"
            staging = transform_jobs(raw)
            top_skills = build_top_skills(staging)
            salary_summary = build_salary_summary(staging)
            daily_stats = build_daily_job_stats(staging)
            validate_analytics(raw, staging, daily_stats, top_skills, salary_summary)
            log_coverage(staging)

            step = "publish staging and marts"
            tables = {
                "stg_jobs": staging,
                "mart_top_skills": top_skills,
                "mart_salary_summary": salary_summary,
                "mart_daily_job_stats": daily_stats,
            }
            for name, rows in tables.items():
                connection.execute(text(f"DELETE FROM {name}"))
                if not rows.empty:
                    rows.to_sql(name, connection, if_exists="append", index=False, chunksize=1000)
        logger.info("Published row counts: %s", {name: len(rows) for name, rows in tables.items()})
    except Exception:
        logger.exception("ETL failed during %s", step)
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    run_pipeline()
