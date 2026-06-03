from apscheduler.schedulers.blocking import BlockingScheduler

from ingest_careerviet_jobs import run_careerviet_ingestion
from pipeline import run_pipeline


def run_job():

    print("=" * 50)
    print("Starting scheduled job")
    print("=" * 50)

    run_careerviet_ingestion()

    run_pipeline()

    print("=" * 50)
    print("Scheduled job completed")
    print("=" * 50)


scheduler = BlockingScheduler()

scheduler.add_job(
    run_job,
    "interval",
    hours=24
)

print("Scheduler started")

run_job()

scheduler.start()