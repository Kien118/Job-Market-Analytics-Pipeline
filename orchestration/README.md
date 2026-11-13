# Operate the Job Market DAG

Start the application PostgreSQL with the root Docker Compose file. If you have an existing database, apply the [database migrations](../README.md#upgrade-an-existing-postgresql-volume) first. Airflow stores its own run metadata separately.

## Start Airflow

From the repo root, set three different random values in the ignored `.env` file for `AIRFLOW_ADMIN_PASSWORD`, `AIRFLOW_DB_PASSWORD` and `AIRFLOW_JWT_SECRET`. Use at least 32 random characters for the JWT secret. For example, run `openssl rand -hex 24` separately for each value.

Airflow connects to the existing application PostgreSQL using `DATABASE_URL`. Run `docker network ls` and set `AIRFLOW_JOB_NETWORK` to the application's Compose network. The example below uses `job-market-analytics` as the base project, so its network is `job-market-analytics_job_market_network`, the default Airflow expects. For an existing database, substitute the project name you used when you started it.

```sh
docker compose -p job-market-analytics --profile etl stop etl
docker compose -p job-market-analytics up -d --wait postgres
docker compose -f compose.airflow.yml up -d --build
docker compose -f compose.airflow.yml exec airflow-scheduler airflow dags list
```

Open [Airflow](http://localhost:8081) and sign in as `admin` with `AIRFLOW_ADMIN_PASSWORD`. In the UI, unpause `job_market`, then use **Trigger** to run it on demand. The DAG schedules at 07:00 in `Asia/Ho_Chi_Minh`, with one active run at a time and catchup disabled. Pause it again to disable the schedule. The Compose stack is intended for local development and demos.

Each source records a separate attempt in `ingestion_runs`. The three tasks can run independently. `publish_analytics` waits for all three and writes staging and marts in one transaction. The reporting snapshot stays available during a failed run, even if successful sources already wrote to raw.

## Diagnose and recover a run

1. In the Airflow Grid, open the run and select the failing source task. Inspect its latest task log and try number. Check for a source HTTP error, a parser rejection, or an unavailable database.
2. Let Airflow retry transient failures. After fixing a persistent failure, clear the failed source task and its downstream tasks **in the same run**. Successful source tasks can stay green.
3. Confirm that `publish_analytics` succeeds. Compare raw and staging counts and inspect the source attempts. An unchanged input replay should keep the same job IDs and add no raw rows.

Use Airflow task state and logs if the worker was killed or PostgreSQL was unavailable during the attempt.

```sql
SELECT source, succeeded, result->>'airflow_try_number' AS try,
       result->>'accepted' AS accepted, result->>'written' AS written,
       result->>'unchanged' AS unchanged, result->>'error' AS error
FROM ingestion_runs
WHERE result->>'airflow_run_id' = 'PASTE_AIRFLOW_RUN_ID'
ORDER BY started_at;

SELECT (SELECT count(*) FROM raw_jobs) AS raw,
       (SELECT count(*) FROM stg_jobs) AS published;
```

For a historical backfill, use saved source snapshots for the target intervals. The live DAG reads current listings.

## Reproduce failure and recovery

Run these commands from the repo root in Bash, including Git Bash on Windows.

```sh
docker build -f orchestration/Dockerfile -t job-market-airflow-test .
bash orchestration/tests/smoke.sh job-market-airflow-test
```

The demo uses disposable PostgreSQL and fixtures. It checks that an HTTP 503 blocks publication, that a successful retry publishes the recovered data, and that replay preserves row IDs and counts.
