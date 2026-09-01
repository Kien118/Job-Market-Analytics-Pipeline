import requests
from datetime import datetime


ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"


def extract_arbeitnow_jobs(limit=20):
    response = requests.get(
        ARBEITNOW_API_URL,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    jobs = data.get("data", [])

    extracted_jobs = []

    for job in jobs[:limit]:
        try:
            extracted_jobs.append(
                {
                    "source": "Arbeitnow",
                    "job_title": job.get("title"),
                    "company_name": job.get("company_name"),
                    "location": job.get("location"),
                    "salary_text": "Not specified",
                    "description": job.get("description", ""),
                    "posted_date": datetime.fromtimestamp(
                        job.get("created_at")
                    ).date(),
                    "source_url": job.get("url"),
                    "external_id": job.get("slug")
                }
            )
        except (AttributeError, TypeError, ValueError, OSError) as error:
            print(f"Skipping invalid Arbeitnow job: {error}")

    return extracted_jobs
