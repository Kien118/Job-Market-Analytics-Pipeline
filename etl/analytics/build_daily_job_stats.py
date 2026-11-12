def build_daily_job_stats(staging):
    return (
        staging
        .groupby("posted_date")
        .size()
        .reset_index(name="total_jobs")
        .sort_values("posted_date")
    )
