import logging

from extract.crawl_careerviet import crawl_careerviet_jobs
from extract.source_batch import ingest_batch


def run_careerviet_ingestion():
    return ingest_batch("CareerViet", crawl_careerviet_jobs(limit=50))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_careerviet_ingestion()
