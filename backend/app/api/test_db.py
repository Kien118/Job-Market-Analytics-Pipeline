from fastapi import APIRouter
from sqlalchemy import text

from app.db.connection import engine

router = APIRouter()


@router.get("/db-test")
def db_test():

    with engine.connect() as conn:

        result = conn.execute(
            text("SELECT 1")
        )

        return {
            "result": result.scalar()
        }