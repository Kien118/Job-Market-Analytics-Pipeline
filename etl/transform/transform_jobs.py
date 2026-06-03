import re


SKILLS = [
    "python",
    "sql",
    "docker",
    "airflow",
    "spark",
    "aws",
    "git",
    "postgresql",
    "fastapi",
    "pandas"
]


def extract_skills(description):
    description = description.lower()

    found_skills = []

    for skill in SKILLS:
        if skill in description:
            found_skills.append(skill)

    return found_skills


def normalize_salary(salary_text):
    if salary_text is None:
        return None, None

    numbers = re.findall(r"\d+", salary_text)

    if len(numbers) == 0:
        return None, None

    if len(numbers) == 1:
        value = float(numbers[0])
        return value, value

    min_salary = float(numbers[0])
    max_salary = float(numbers[1])

    return min_salary, max_salary


def detect_seniority(title):
    title = title.lower()

    if "intern" in title:
        return "Intern"

    if "fresher" in title:
        return "Fresher"

    if "junior" in title:
        return "Junior"

    if "senior" in title:
        return "Senior"

    return "Unknown"


def transform_jobs(df):
    if df.empty:
        print("No raw jobs found. Skip transform.")
        return df

    df["clean_title"] = df["job_title"].str.strip()
    df["clean_location"] = df["location"].str.strip()

    salary_df = df["salary_text"].apply(
        lambda x: normalize_salary(x)
    ).apply(
        lambda x: __import__("pandas").Series(x)
    )

    salary_df.columns = ["min_salary", "max_salary"]

    df = __import__("pandas").concat(
        [df, salary_df],
        axis=1
    )

    df["seniority"] = df["job_title"].apply(detect_seniority)
    df["skills"] = df["description"].apply(extract_skills)

    return df[
        [
            "job_id",
            "clean_title",
            "clean_location",
            "min_salary",
            "max_salary",
            "seniority",
            "skills"
        ]
    ]