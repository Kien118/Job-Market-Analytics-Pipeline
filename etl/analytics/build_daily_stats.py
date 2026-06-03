def build_daily_stats(raw_df):

    result = (
        raw_df.groupby("posted_date")
        .size()
        .reset_index(name="total_jobs")
    )

    return result