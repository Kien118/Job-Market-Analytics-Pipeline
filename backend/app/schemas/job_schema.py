from datetime import date

from pydantic import BaseModel


class JobCreate(BaseModel):

    source: str

    job_title: str

    company_name: str

    location: str

    salary_text: str

    description: str

    posted_date: date

    source_url: str | None = None

    external_id: str | None = None
