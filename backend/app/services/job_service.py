import hashlib

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.job import RawJob


def generate_job_hash(job_title, company_name, location):
    key = (
        f"{job_title or ''}|"
        f"{company_name or ''}|"
        f"{location or ''}"
    )

    return hashlib.md5(
        key.lower().strip().encode("utf-8")
    ).hexdigest()


def create_job(db: Session, job_data):
    job_hash = generate_job_hash(
        job_data.job_title,
        job_data.company_name,
        job_data.location
    )

    statement = insert(RawJob).values(
        source=job_data.source,
        job_title=job_data.job_title,
        company_name=job_data.company_name,
        location=job_data.location,
        salary_text=job_data.salary_text,
        description=job_data.description,
        posted_date=job_data.posted_date,
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
