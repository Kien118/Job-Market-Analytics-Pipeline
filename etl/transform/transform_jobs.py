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
    if not isinstance(description, str):
        return []

    description = description.lower()

    found_skills = []

    for skill in SKILLS:
        if skill in description:
            found_skills.append(skill)

    return found_skills


def normalize_salary(salary_text):
    if not isinstance(salary_text, str):
        return None, None

    normalized_text = re.sub(
        r"(?<=\d)[,.](?=\d{3}(?:[,.]\d{3})*(?!\d))",
        "",
        salary_text
    )

    numbers = [
        float(value.replace(",", "."))
        for value in re.findall(r"\d+(?:[.,]\d+)?", normalized_text)
    ]

    if len(numbers) == 0:
        return None, None

    if len(numbers) == 1:
        value = numbers[0]
        return value, value

    min_salary = numbers[0]
    max_salary = numbers[1]

    return min_salary, max_salary


def detect_seniority(title):
    if not isinstance(title, str):
        return "Unknown"

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

    df["clean_title"] = df["job_title"].fillna("").astype(str).str.strip()
    df["clean_location"] = df["location"].fillna("").astype(str).str.strip()

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
