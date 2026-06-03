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