from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.db.session import get_db

from app.schemas.job_schema import JobCreate

from app.services.job_service import (
    create_job,
    get_jobs
)

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


@router.post("/ingest")
def ingest_job(
    job: JobCreate,
    db: Session = Depends(get_db)
):

    return create_job(db, job)


@router.get("/")
def list_jobs(
    db: Session = Depends(get_db)
):

    return get_jobs(db)