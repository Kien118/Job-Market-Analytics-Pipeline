from extract.crawl_careerviet import crawl_careerviet_jobs
from load.load_raw_jobs import load_raw_jobs


def run_careerviet_ingestion():
    print("Starting CareerViet crawler ingestion...")

    jobs = crawl_careerviet_jobs(limit=50)

    print(f"Crawled {len(jobs)} jobs from CareerViet")

    load_raw_jobs(jobs)

    print("CareerViet crawler ingestion completed successfully")


if __name__ == "__main__":
    run_careerviet_ingestion()