import logging

from extract.extract_arbeitnow import extract_arbeitnow_jobs
from extract.source_batch import ingest_batch


def run_api_ingestion():
    return ingest_batch("Arbeitnow", extract_arbeitnow_jobs(limit=20))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_api_ingestion()
