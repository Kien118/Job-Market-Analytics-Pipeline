from extract.extract_arbeitnow import extract_arbeitnow_jobs
from load.load_raw_jobs import load_raw_jobs


def run_api_ingestion():
    print("Starting API job ingestion...")

    jobs = extract_arbeitnow_jobs(limit=20)

    print(f"Extracted {len(jobs)} jobs from Arbeitnow API")

    load_raw_jobs(jobs)

    print("API job ingestion completed successfully")


if __name__ == "__main__":
    run_api_ingestion()