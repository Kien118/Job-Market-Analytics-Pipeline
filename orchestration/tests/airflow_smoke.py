"""Exercise the real Airflow DAG against fixture HTTP and disposable PostgreSQL."""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.parse import urlsplit

from requests import Response
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


DATABASE_NAME = "job_market_airflow_smoke"
LISTING = {
    "careerviet.vn": '<a href="/vi/tim-viec-lam/fixture.html">Data Engineer CareerViet Fixture</a>',
    "topdev.vn": '<a href="/detail-jobs/data-engineer-fixture">Data Engineer TopDev Fixture</a>',
}
DETAIL = """<h1>Data Engineer Fixture</h1>
<script type="application/ld+json">
{"@type":"JobPosting","datePosted":"2026-01-02","description":"Python and SQL"}
</script>"""
ARBEITNOW = """{"data":[{
    "slug":"airflow-fixture","title":"Analytics Engineer Fixture","location":"Berlin",
    "description":"Apache Spark and SQL","created_at":1767312000,"url":"https://www.arbeitnow.com/jobs/fixture"
}]}"""
MARTS = ("stg_jobs", "mart_top_skills", "mart_salary_summary", "mart_daily_job_stats")


def response(url, body, status=200):
    result = Response()
    result.url = url
    result.status_code = status
    result.encoding = "utf-8"
    result._content = body.encode()
    return result


def fixture_http(url, *, fail_arbeitnow, **_kwargs):
    parts = urlsplit(url)
    if parts.hostname == "www.arbeitnow.com" and parts.path == "/api/job-board-api":
        if fail_arbeitnow():
            return response(url, "Fixture outage", 503)
        return response(url, ARBEITNOW)
    if parts.hostname in LISTING:
        if parts.path.startswith(("/vi/tim-viec-lam/", "/detail-jobs/")):
            return response(url, DETAIL)
        return response(url, LISTING[parts.hostname])
    raise AssertionError(f"Unexpected source URL in smoke test: {url}")


def main():
    url = make_url(os.environ["DATABASE_URL"])
    if url.database != DATABASE_NAME or url.host != "smoke-postgres":
        raise RuntimeError("Smoke test requires its disposable PostgreSQL container")
    engine = create_engine(url, poolclass=NullPool, hide_parameters=True)

    def rows(sql, **parameters):
        with engine.connect() as connection:
            return connection.execute(text(sql), parameters).all()

    def published_snapshot():
        return tuple(
            rows(f"SELECT to_jsonb(published) - 'transformed_at' FROM {table} AS published ORDER BY 1")
            for table in MARTS
        )

    def raw_ids():
        jobs = rows("SELECT source, job_id FROM raw_jobs ORDER BY job_id")
        ids = dict(jobs)
        assert len(ids) == len(jobs), jobs
        return ids

    def failures():
        return rows("SELECT count(*) FROM ingestion_runs WHERE source = 'arbeitnow' AND NOT succeeded")[0][0]

    def attempts(run_id):
        return rows("""
            SELECT source, succeeded, result
            FROM ingestion_runs WHERE result->>'airflow_run_id' = :run_id
            ORDER BY source, started_at
        """, run_id=run_id)

    # Imports follow the database guard so even a misconfigured smoke cannot call ETL.
    from job_market import job_market as dag
    from pipeline import run_pipeline

    with engine.begin() as connection:
        occupied = connection.scalar(text("SELECT EXISTS (SELECT 1 FROM raw_jobs UNION ALL SELECT 1 FROM ingestion_runs)"))
        if occupied:
            raise RuntimeError("Smoke database already contains rows")
        connection.execute(text("""
            SELECT * FROM public.upsert_raw_job(
                'Smoke Seed', 'Data Engineer', 'Fixture', 'Hà Nội', NULL, 'Python',
                DATE '2026-01-01', NULL, 'seed'
            )
        """))
    run_pipeline()
    published_before = published_snapshot()
    assert tuple(map(len, published_before)) == (1, 1, 0, 1), published_before

    source_task = dag.get_task("ingest_arbeitnow")
    assert source_task.retries > 0
    source_task.retry_exponential_backoff = False
    source_task.retry_delay = timedelta()
    logical_date = datetime.now(timezone.utc) - timedelta(minutes=3)

    def run(offset, fail_arbeitnow):
        def get(url, **kwargs):
            return fixture_http(url, fail_arbeitnow=fail_arbeitnow, **kwargs)
        with patch("requests.get", get):
            return dag.test(logical_date=logical_date + timedelta(minutes=offset))

    failed = run(0, lambda: True)
    assert failed.state == "failed", failed.state
    assert failed.get_task_instance("ingest_careerviet").state == "success"
    assert failed.get_task_instance("ingest_topdev").state == "success"
    assert failed.get_task_instance("ingest_arbeitnow").state == "failed"
    assert failed.get_task_instance("publish_analytics").state == "upstream_failed"
    failed_raw = raw_ids()
    assert set(failed_raw) == {"Smoke Seed", "CareerViet", "TopDev"}, failed_raw
    assert published_snapshot() == published_before
    failed_attempt_count = failures()
    assert failed_attempt_count == source_task.retries + 1, failed_attempt_count
    failure_attempts = [
        result for source, succeeded, result in attempts(failed.run_id)
        if source == "arbeitnow" and not succeeded
    ]
    assert [result["airflow_try_number"] for result in failure_attempts] == list(range(1, failed_attempt_count + 1))
    assert all(result["error"] == "HTTPError" for result in failure_attempts), failure_attempts
    print("HTTP 503 exhausted retries. Healthy sources committed raw. Published snapshot stayed unchanged.", flush=True)

    recovered = run(1, lambda: failures() == failed_attempt_count)
    assert recovered.state == "success", recovered.state
    assert recovered.get_task_instance("publish_analytics").state == "success"
    recovered_attempts = attempts(recovered.run_id)
    recovered_source = [(succeeded, result) for source, succeeded, result in recovered_attempts if source == "arbeitnow"]
    assert [succeeded for succeeded, _ in recovered_source] == [False, True], recovered_attempts
    assert [result["airflow_try_number"] for _, result in recovered_source] == [1, 2], recovered_attempts
    recovered_raw = raw_ids()
    assert set(recovered_raw) == {*failed_raw, "Arbeitnow"}, recovered_raw
    assert all(recovered_raw[source] == job_id for source, job_id in failed_raw.items()), recovered_raw
    published_after = published_snapshot()
    assert tuple(map(len, published_after)) == (4, 3, 0, 2), published_after
    print("Airflow retried the transient failure and published all four postings.", flush=True)

    replayed = run(2, lambda: False)
    assert replayed.state == "success", replayed.state
    assert raw_ids() == recovered_raw
    assert published_snapshot() == published_after
    replay_attempts = attempts(replayed.run_id)
    assert len(replay_attempts) == 3 and all(
        succeeded and result["unchanged"] == 1 and result["written"] == 0
        for _, succeeded, result in replay_attempts
    ), replay_attempts
    print("Replayed the same inputs. Raw IDs, row counts and published metrics stayed stable.", flush=True)
    engine.dispose()


if __name__ == "__main__":
    main()
