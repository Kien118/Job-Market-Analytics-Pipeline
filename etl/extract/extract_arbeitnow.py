from datetime import datetime, timezone

import requests

from extract.source_batch import SourceBatch


ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"


def extract_arbeitnow_jobs(limit=20):
    response = requests.get(ARBEITNOW_API_URL, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("Arbeitnow response must contain a data array")

    batch = SourceBatch()
    for job in payload["data"][:limit]:
        if not isinstance(job, dict):
            batch.reject("Arbeitnow record is not an object")
            continue
        try:
            created_at = job.get("created_at")
            if created_at is not None and type(created_at) not in {int, float}:
                raise ValueError("created_at must be a numeric Unix timestamp")
            posted = datetime.fromtimestamp(created_at, timezone.utc).date() if created_at is not None else None
        except (OverflowError, ValueError, OSError) as error:
            batch.reject(error)
            continue

        batch.add({
            "source": "Arbeitnow",
            "job_title": job.get("title"),
            "company_name": job.get("company_name"),
            "location": job.get("location"),
            "description": job.get("description"),
            "posted_date": posted,
            "source_url": job.get("url"),
            "external_id": job.get("slug"),
        })
    return batch
