import hashlib
import math

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.job import RawJob


def normalize_hash_value(value):
    if value is None:
        return ""

    try:
        if math.isnan(value):
            return ""
    except (TypeError, ValueError):
        pass

    return str(value).strip().lower()


def generate_job_hash(
    source,
    job_title,
    company_name,
    location,
    source_url=None,
    external_id=None
):
    normalized_source_url = normalize_hash_value(source_url).rstrip("/")
    normalized_external_id = normalize_hash_value(external_id)

    if normalized_source_url:
        key = f"url|{normalized_source_url}"
    elif normalized_external_id:
        key = (
            f"external|{normalize_hash_value(source)}|"
            f"{normalized_external_id}"
        )
    else:
        key = (
            f"content|{normalize_hash_value(job_title)}|"
            f"{normalize_hash_value(company_name)}|"
            f"{normalize_hash_value(location)}"
        )

    return hashlib.md5(
        key.encode("utf-8")
    ).hexdigest()


def create_job(db: Session, job_data):
    job_hash = generate_job_hash(
        job_data.source,
        job_data.job_title,
        job_data.company_name,
        job_data.location,
        job_data.source_url,
        job_data.external_id
    )

    statement = insert(RawJob).values(
        source=job_data.source,
        job_title=job_data.job_title,
        company_name=job_data.company_name,
        location=job_data.location,
        salary_text=job_data.salary_text,
        description=job_data.description,
        posted_date=job_data.posted_date,
        source_url=job_data.source_url,
        external_id=job_data.external_id,
        job_hash=job_hash
    ).on_conflict_do_nothing(
        index_elements=[RawJob.job_hash]
    ).returning(
        RawJob.job_id
    )

    job_id = db.execute(statement).scalar_one_or_none()

    if job_id is None:
        job = db.query(RawJob).filter(
            RawJob.job_hash == job_hash
        ).one()
    else:
        job = db.query(RawJob).filter(
            RawJob.job_id == job_id
        ).one()

    db.commit()
    db.refresh(job)

    return job


def get_jobs(db: Session):

    return db.query(RawJob).all()
