from datetime import date
from typing import Annotated

from pydantic import BaseModel, StringConstraints


class JobCreate(BaseModel):

    source: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

    job_title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

    company_name: str

    location: str

    salary_text: str

    description: str

    posted_date: date

    source_url: str | None = None

    external_id: str | None = None
