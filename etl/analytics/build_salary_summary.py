import pandas as pd


def build_salary_summary(df):

    salary_df = df.dropna(
        subset=["max_salary"]
    )

    if salary_df.empty:

        return pd.DataFrame(
            columns=[
                "clean_location",
                "avg_salary"
            ]
        )

    result = (
        salary_df
        .groupby("clean_location")
        .agg(
            avg_salary=(
                "max_salary",
                "mean"
            )
        )
        .reset_index()
    )

    return result