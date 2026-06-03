from fastapi import FastAPI
from app.api.jobs import router as jobs_router
from app.api.test_db import router as test_router


app = FastAPI(
    title="Job Market Analytics Pipeline API",
    version="1.0.0"
)


app.include_router(test_router)
app.include_router(jobs_router)

@app.get("/")
def root():
    return {
        "message": "Job Market Analytics Pipeline API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }