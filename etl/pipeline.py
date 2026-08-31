import logging

from extract.extract_raw_jobs import extract_raw_jobs
from transform.transform_jobs import transform_jobs
from load.load_stg_jobs import load_stg_jobs

from analytics.build_top_skills import build_top_skills
from load.load_top_skills import load_top_skills

from analytics.build_salary_summary import (
    build_salary_summary
)

from load.load_salary_summary import (
    load_salary_summary
)

from analytics.build_daily_job_stats import build_daily_job_stats
from load.load_daily_job_stats import load_daily_job_stats


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)

logger = logging.getLogger(__name__)


def run_pipeline():
    logger.info("Starting ETL pipeline")

    try:
        raw_df = extract_raw_jobs()
        logger.info("Extracted %s raw jobs", len(raw_df))
    except Exception:
        logger.exception("ETL step failed: extract raw jobs")
        raise

    try:
        transformed_df = transform_jobs(raw_df)
        logger.info("Transformed %s jobs", len(transformed_df))
    except Exception:
        logger.exception("ETL step failed: transform jobs")
        raise

    try:
        load_stg_jobs(transformed_df)
        logger.info("ETL step completed: load staging jobs")
    except Exception:
        logger.exception("ETL step failed: load staging jobs")
        raise

    # Analytics Mart
    try:
        top_skills_df = build_top_skills(
            transformed_df
        )
        logger.info("ETL step completed: build top skills")
    except Exception:
        logger.exception("ETL step failed: build top skills")
        raise

    try:
        load_top_skills(top_skills_df)
        logger.info("ETL step completed: load top skills")
    except Exception:
        logger.exception("ETL step failed: load top skills")
        raise

    try:
        salary_summary_df = build_salary_summary(transformed_df)
        logger.info("ETL step completed: build salary summary")
    except Exception:
        logger.exception("ETL step failed: build salary summary")
        raise

    try:
        load_salary_summary(salary_summary_df)
        logger.info("ETL step completed: load salary summary")
    except Exception:
        logger.exception("ETL step failed: load salary summary")
        raise

    try:
        daily_job_stats_df = build_daily_job_stats(raw_df)
        logger.info("ETL step completed: build daily job stats")
    except Exception:
        logger.exception("ETL step failed: build daily job stats")
        raise

    try:
        load_daily_job_stats(daily_job_stats_df)
        logger.info("ETL step completed: load daily job stats")
    except Exception:
        logger.exception("ETL step failed: load daily job stats")
        raise

    logger.info("ETL pipeline completed successfully")


if __name__ == "__main__":
    run_pipeline()
