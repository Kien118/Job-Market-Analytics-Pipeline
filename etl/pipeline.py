from extract.extract_raw_jobs import extract_raw_jobs
from transform.transform_jobs import transform_jobs
from load.load_stg_jobs import load_stg_jobs


def run_pipeline():
    print("Starting ETL pipeline...")

    raw_df = extract_raw_jobs()
    print(f"Extracted {len(raw_df)} raw jobs")

    transformed_df = transform_jobs(raw_df)
    print(f"Transformed {len(transformed_df)} jobs")

    load_stg_jobs(transformed_df)

    print("ETL pipeline completed successfully")


if __name__ == "__main__":
    run_pipeline()