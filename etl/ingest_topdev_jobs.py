import logging

from extract.crawl_topdev import crawl_topdev_jobs
from extract.source_batch import ingest_batch


def run_topdev_ingestion():
    return ingest_batch("TopDev", crawl_topdev_jobs(limit=50))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_topdev_ingestion()
