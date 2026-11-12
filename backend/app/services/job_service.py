from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.job import RawJob


def create_job(db: Session, job_data):
    statement = text("""
        SELECT job_id FROM public.upsert_raw_job(
            :source, :job_title, :company_name, :location, :salary_text,
            :description, :posted_date, :source_url, :external_id
        )
    """)
    job_id = db.execute(statement, job_data.model_dump()).scalar_one()
    job = db.get(RawJob, job_id)
    db.commit()
    db.refresh(job)
    return job


def get_jobs(db: Session, limit: int, offset: int):
    return db.query(RawJob).order_by(RawJob.job_id.desc()).offset(offset).limit(limit).all()
