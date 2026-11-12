def build_top_skills(staging):
    return (
        staging["skills"]
        .explode()
        .dropna()
        .value_counts()
        .rename_axis("skill_name")
        .reset_index(name="total_jobs")
        .sort_values(["total_jobs", "skill_name"], ascending=[False, True])
    )
