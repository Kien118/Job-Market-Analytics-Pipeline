from datetime import timedelta

import pendulum
from airflow.sdk import dag, get_current_context, task


@dag(
    dag_id="job_market",
    schedule="0 7 * * *",
    start_date=pendulum.datetime(2026, 1, 1, tz="Asia/Ho_Chi_Minh"),
    catchup=False,
    max_active_runs=1,
    is_paused_upon_creation=True,
)
def job_market_dag():
    @task(
        retries=2,
        retry_delay=timedelta(minutes=2),
        retry_exponential_backoff=True,
        max_retry_delay=timedelta(minutes=10),
        execution_timeout=timedelta(minutes=15),
        do_xcom_push=False,
    )
    def ingest_source(source):
        from source_runs import run_source_attempt

        ti = get_current_context()["ti"]
        run_source_attempt(source, airflow_run_id=ti.run_id, airflow_try_number=ti.try_number)

    @task(
        trigger_rule="all_success",
        retries=1,
        retry_delay=timedelta(minutes=2),
        execution_timeout=timedelta(minutes=15),
        do_xcom_push=False,
    )
    def publish_analytics():
        from pipeline import run_pipeline

        run_pipeline()

    sources = [
        ingest_source.override(task_id=f"ingest_{source}")(source)
        for source in ("careerviet", "topdev", "arbeitnow")
    ]
    sources >> publish_analytics()


job_market = job_market_dag()
