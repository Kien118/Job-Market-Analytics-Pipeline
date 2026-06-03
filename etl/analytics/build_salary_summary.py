def build_salary_summary(df):

    result = (
        df.groupby("clean_location")
        .agg(
            avg_salary=(
                "max_salary",
                "mean"
            )
        )
        .reset_index()
    )

    return result