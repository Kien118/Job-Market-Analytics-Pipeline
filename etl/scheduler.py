import argparse
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import create_engine

from pipeline import run_pipeline
from source_runs import INGESTIONS, record_source_run


logger = logging.getLogger(__name__)


def selected_sources():
    value = os.getenv("INGEST_SOURCES", ",".join(INGESTIONS))
    sources = list(dict.fromkeys(part.strip().lower() for part in value.split(",") if part.strip()))
    if not sources or any(source not in INGESTIONS for source in sources):
        raise ValueError("INGEST_SOURCES must list one or more of: " + ", ".join(INGESTIONS))
    return sources


def run_job(sources):
    run_id = uuid4()
    engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/job_market_db"))
    failed = []
    try:
        for source in sources:
            started_at = datetime.now(timezone.utc)
            try:
                result = INGESTIONS[source]()
            except Exception as error:
                logger.exception("Ingestion failed for %s (run %s)", source, run_id)
                failed.append(source)
                record_source_run(engine, run_id, source, started_at, False, {"error": type(error).__name__})
            else:
                record_source_run(engine, run_id, source, started_at, True, result)
    finally:
        engine.dispose()
    if failed:
        raise RuntimeError(f"Reporting refresh skipped after failed ingestion: {', '.join(failed)}")

    run_pipeline()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run ingestion and reporting once")
    args = parser.parse_args()
    sources = selected_sources()
    if args.once:
        run_job(sources)
        return

    scheduler = BlockingScheduler(timezone=timezone.utc)
    scheduler.add_job(
        run_job,
        "cron",
        hour=0,
        args=[sources],
        next_run_time=datetime.now(timezone.utc),
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
