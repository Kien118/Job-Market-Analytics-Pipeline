#!/usr/bin/env bash
set -euo pipefail

image=${1:?Usage: bash orchestration/tests/smoke.sh IMAGE}
cd "$(dirname "$0")/../.."
network="job-market-airflow-smoke-$$-$RANDOM"
postgres="${network}-db"
airflow="${network}-worker"
cleanup() {
    docker rm -f "$airflow" >/dev/null 2>&1 || true
    docker rm -f "$postgres" >/dev/null 2>&1 || true
    docker network rm "$network" >/dev/null 2>&1 || true
}
docker network create --internal "$network" >/dev/null
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
docker run -d --rm --name "$postgres" --network "$network" --network-alias smoke-postgres \
    -e POSTGRES_DB=job_market_airflow_smoke -e POSTGRES_PASSWORD=fixture postgres:16 >/dev/null

for _ in {1..30}; do
    if docker exec "$postgres" pg_isready -h 127.0.0.1 -U postgres -d job_market_airflow_smoke; then
        break
    fi
    sleep 1
done
docker exec "$postgres" pg_isready -h 127.0.0.1 -U postgres -d job_market_airflow_smoke >/dev/null
MSYS_NO_PATHCONV=1 docker cp database/init/. "$postgres:/tmp/job-market-init"
MSYS_NO_PATHCONV=1 docker exec "$postgres" sh -ec '
    for migration in /tmp/job-market-init/*.sql; do
        psql -q -v ON_ERROR_STOP=1 -U postgres -d job_market_airflow_smoke -f "$migration"
    done
'

MSYS_NO_PATHCONV=1 docker run --rm --name "$airflow" --network "$network" --entrypoint /bin/bash \
    -e DATABASE_URL=postgresql://postgres:fixture@smoke-postgres:5432/job_market_airflow_smoke \
    -e AIRFLOW_HOME=/tmp/job-market-airflow-smoke \
    -e AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=sqlite:////tmp/job-market-airflow-smoke/airflow.db \
    -e AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags -e AIRFLOW__CORE__LOAD_EXAMPLES=False \
    -e PYTHONPATH=/opt/airflow/etl:/opt/airflow/dags \
    "$image" -ec 'mkdir -p "$AIRFLOW_HOME"; airflow db migrate; python /opt/airflow/tests/airflow_smoke.py'
