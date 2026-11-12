from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.jobs import router as jobs_router
from app.db.connection import engine


app = FastAPI(
    title="Job Market Analytics Pipeline API",
    version="1.0.0"
)


app.include_router(jobs_router)

@app.get("/")
def root():
    return {
        "message": "Job Market Analytics Pipeline API is running"
    }


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {
        "status": "healthy"
    }
