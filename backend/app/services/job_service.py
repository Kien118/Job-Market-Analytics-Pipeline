from sqlalchemy.orm import Session

from app.models.job import RawJob


def create_job(db: Session, job_data):

    job = RawJob(
        source=job_data.source,
        job_title=job_data.job_title,
        company_name=job_data.company_name,
        location=job_data.location,
        salary_text=job_data.salary_text,
        description=job_data.description,
        posted_date=job_data.posted_date
    )

    db.add(job)

    db.commit()

    db.refresh(job)

    return job


def get_jobs(db: Session):

    return db.query(RawJob).all()