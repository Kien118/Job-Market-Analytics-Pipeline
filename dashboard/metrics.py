def filter_postings(postings, sources, locations, posted_range):
    mask = postings["source"].isin(sources) & postings["clean_location"].isin(locations)
    if len(posted_range) == 2:
        first_day, last_day = posted_range
        mask &= postings["posted_date"].between(first_day, last_day)
    return postings.loc[mask]


def skill_counts(postings):
    described = postings.loc[postings["has_description"].eq(True).fillna(False)]
    mentions = (
        described[["job_id", "skills"]]
        .explode("skills")
        .rename(columns={"skills": "skill_name"})
        .dropna(subset=["skill_name"])
    )
    counts = (
        mentions.groupby("skill_name")["job_id"]
        .nunique()
        .reset_index(name="total_jobs")
        .sort_values(["total_jobs", "skill_name"], ascending=[False, True])
    )
    counts["share"] = counts["total_jobs"] / len(described)
    return counts, len(described)


def daily_postings(postings):
    return postings.groupby("posted_date", sort=True).size().reset_index(name="total_jobs")


def monthly_vnd_salaries(postings):
    monthly = postings.loc[
        postings["salary_currency"].eq("VND") & postings["salary_period"].eq("month")
    ].dropna(subset=["min_salary", "max_salary"])
    midpoints = (monthly["min_salary"] + monthly["max_salary"]) / 2
    return (
        monthly.assign(midpoint=midpoints)
        .groupby("clean_location", as_index=False)
        .agg(avg_salary=("midpoint", "mean"), total_jobs=("job_id", "size"))
    )


def search_postings(postings, text):
    keyword = text.strip()
    if not keyword:
        return postings
    folded_keyword = keyword.casefold()
    return postings.loc[
        postings["clean_title"].str.contains(keyword, case=False, regex=False, na=False)
        | postings["skills"].map(
            lambda skills: any(folded_keyword in skill.casefold() for skill in (skills or []))
        )
    ]
