import pandas as pd


def build_top_skills(df):

    rows = []

    for _, row in df.iterrows():

        skills = row["skills"]

        if not skills:
            continue

        for skill in skills:

            rows.append(
                {
                    "skill_name": skill
                }
            )

    skill_df = pd.DataFrame(rows)

    result = (
        skill_df
        .groupby("skill_name")
        .size()
        .reset_index(name="total_jobs")
        .sort_values(
            "total_jobs",
            ascending=False
        )
    )

    return result