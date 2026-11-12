from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


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


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    source: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    location: str | None = None
    salary_text: str | None = None
    description: str | None = None
    posted_date: date | None = None
    source_url: str | None = None
    external_id: str | None = None
    ingested_at: datetime | None = None


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    skip: int
    limit: int
