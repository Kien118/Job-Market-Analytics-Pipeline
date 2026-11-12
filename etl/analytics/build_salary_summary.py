def build_salary_summary(staging):
    salaries = staging.dropna(
        subset=["min_salary", "max_salary", "salary_currency", "salary_period"]
    ).copy()
    salaries["midpoint"] = (salaries["min_salary"] + salaries["max_salary"]) / 2
    return (
        salaries.groupby(["clean_location", "salary_currency", "salary_period"])
        .agg(avg_salary=("midpoint", "mean"), sample_count=("midpoint", "size"))
        .reset_index()
    )
