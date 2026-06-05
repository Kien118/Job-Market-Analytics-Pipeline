from extract.crawl_topdev import crawl_topdev_jobs
from load.load_raw_jobs import load_raw_jobs


def run_topdev_ingestion():
    print("Starting TopDev crawler ingestion...")

    jobs = crawl_topdev_jobs(limit=50)

    print(f"Crawled {len(jobs)} jobs from TopDev")

    load_raw_jobs(jobs)

    print("TopDev crawler ingestion completed successfully")


if __name__ == "__main__":
    run_topdev_ingestion()