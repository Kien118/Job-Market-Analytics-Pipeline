import json
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine, text

from ingest_api_jobs import run_api_ingestion
from ingest_careerviet_jobs import run_careerviet_ingestion
from ingest_topdev_jobs import run_topdev_ingestion


logger = logging.getLogger(__name__)
INGESTIONS = {
    "careerviet": run_careerviet_ingestion,
    "topdev": run_topdev_ingestion,
    "arbeitnow": run_api_ingestion,
}


def record_source_run(engine, run_id, source, started_at, succeeded, result):
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO ingestion_runs (run_id, source, started_at, completed_at, succeeded, result)
                VALUES (:run_id, :source, :started_at, CURRENT_TIMESTAMP, :succeeded, CAST(:result AS JSONB))
            """),
            {
                "run_id": run_id,
                "source": source,
                "started_at": started_at,
                "succeeded": succeeded,
                "result": json.dumps(result),
            },
        )


def run_source_attempt(source, *, airflow_run_id, airflow_try_number):
    run_id = uuid4()
    started_at = datetime.now(timezone.utc)
    context = {
        "airflow_run_id": airflow_run_id,
        "airflow_try_number": airflow_try_number,
    }
    engine = create_engine(os.environ["DATABASE_URL"], hide_parameters=True)
    logger.info("Starting %s ingestion attempt %s (%s)", source, run_id, context)
    try:
        try:
            result = INGESTIONS[source]()
        except BaseException as error:
            # Airflow's execution timeout bypasses Exception. Record the attempt and re-raise it.
            try:
                record_source_run(
                    engine, run_id, source, started_at, False,
                    {**context, "error": type(error).__name__},
                )
            except Exception:
                logger.exception("Could not record %s ingestion failure for attempt %s", source, run_id)
            raise
        record_source_run(engine, run_id, source, started_at, True, {**result, **context})
        logger.info("Completed %s ingestion attempt %s (%s)", source, run_id, result)
    finally:
        engine.dispose()
