from secrets import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings

from app.schemas.job_schema import JobCreate, JobListResponse

from app.services.job_service import (
    create_job,
    get_jobs
)

def require_api_key(x_api_key: str = Header(default="")):
    if not settings.JOB_API_KEY:
        raise HTTPException(status_code=503, detail="Job API is disabled")
    if not compare_digest(x_api_key.encode(), settings.JOB_API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
    dependencies=[Depends(require_api_key)]
)


@router.post("/ingest")
def ingest_job(
    job: JobCreate,
    db: Session = Depends(get_db)
):

    return create_job(db, job)


@router.get("/", response_model=JobListResponse)
def list_jobs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int | None = Query(default=None, ge=0),
    db: Session = Depends(get_db)
):

    return get_jobs(db, offset if offset is not None else skip, limit)
