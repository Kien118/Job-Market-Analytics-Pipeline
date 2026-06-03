def build_daily_job_stats(raw_df):
    if raw_df.empty:
        return raw_df

    result = (
        raw_df
        .groupby("posted_date")
        .size()
        .reset_index(name="total_jobs")
        .sort_values("posted_date")
    )

    return result