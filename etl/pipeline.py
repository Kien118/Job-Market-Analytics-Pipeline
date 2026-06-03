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


def run_pipeline():

    print("Starting ETL pipeline...")

    raw_df = extract_raw_jobs()
    print(f"Extracted {len(raw_df)} raw jobs")

    transformed_df = transform_jobs(raw_df)
    print(f"Transformed {len(transformed_df)} jobs")

    load_stg_jobs(transformed_df)

    # Analytics Mart
    top_skills_df = build_top_skills(
        transformed_df
    )

    load_top_skills(
        top_skills_df
    )

    salary_summary_df = (
        build_salary_summary(
            transformed_df
        )
    )
    load_salary_summary(
        salary_summary_df
    )

    daily_job_stats_df = build_daily_job_stats(raw_df)

    load_daily_job_stats(daily_job_stats_df)

    print("Daily job stats mart created")

    print(
    "Salary mart created"
    )

    print("Top skills mart created")

    print("ETL pipeline completed successfully")


if __name__ == "__main__":
    run_pipeline()