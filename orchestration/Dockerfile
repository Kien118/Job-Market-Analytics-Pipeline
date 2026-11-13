FROM apache/airflow:3.2.2-python3.12

COPY --chown=airflow:root etl/requirement.txt /opt/airflow/etl-requirements.txt
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" \
    -r /opt/airflow/etl-requirements.txt --constraint "${HOME}/constraints.txt" \
    && mkdir -p /opt/airflow/auth

COPY --chown=airflow:root etl/ /opt/airflow/etl/
COPY --chown=airflow:root orchestration/dags/ /opt/airflow/dags/
COPY --chown=airflow:root orchestration/tests/ /opt/airflow/tests/
ENV PYTHONPATH=/opt/airflow/etl
