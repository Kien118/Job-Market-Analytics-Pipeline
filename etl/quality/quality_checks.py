import logging

import pandas as pd


logger = logging.getLogger(__name__)


def validate_analytics(raw, staging, daily_stats, top_skills, salary_summary):
    if (
        staging["job_id"].isna().any()
        or not staging["job_id"].is_unique
        or len(staging) != len(raw)
        or set(staging["job_id"]) != set(raw["job_id"])
    ):
        raise ValueError("Staging must contain exactly one row for each raw job ID")

    if daily_stats["total_jobs"].sum() != staging["posted_date"].notna().sum():
        raise ValueError("Daily postings do not reconcile with the dated jobs in staging")

    if top_skills["total_jobs"].sum() != staging["skills"].map(len).sum():
        raise ValueError("Skill counts do not reconcile with the skill mentions in staging")

    salary_fields = ["min_salary", "max_salary", "salary_currency", "salary_period"]
    salary_known = staging[salary_fields].notna()
    if (salary_known.any(axis=1) != salary_known.all(axis=1)).any():
        raise ValueError("Parsed salary is missing an amount, currency or period")
    if salary_summary["sample_count"].sum() != salary_known.all(axis=1).sum():
        raise ValueError("Salary samples do not reconcile with the parsed salaries in staging")


def log_coverage(staging):
    for source, jobs in staging.groupby("source"):
        posted = pd.to_datetime(jobs["posted_date"], errors="coerce")
        ingested = pd.to_datetime(jobs["ingested_at"], errors="coerce")
        # A long posting-to-collection gap is useful to track even when the crawl itself succeeds.
        late = ingested.dt.normalize() - posted > pd.Timedelta(days=7)
        logger.info(
            "Source coverage: source=%r jobs=%d missing_title=%d missing_posted_date=%d "
            "missing_description=%d comparable_salary=%d posted_over_7_days_before_ingestion=%d "
            "latest_ingested_at=%s",
            source, len(jobs), jobs["clean_title"].eq("").sum(), jobs["posted_date"].isna().sum(),
            (~jobs["has_description"]).sum(), jobs["salary_currency"].notna().sum(),
            late.sum(), ingested.max(),
        )
